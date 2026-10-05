# -*- coding: utf-8 -*-
"""
去水印工具（本地 AI 修复版）
============================
用本地 ComfyUI（SD 1.5 img2img）对「底图」里的图片做 AI 修复重绘，
把平铺的淡水印（文字/斜线/小印记）在重绘中抹掉，结果输出到「无水印」。

用法：双击「去水印AI.bat」，或
    python remove_watermark_ai.py [--src 底图] [--dst 无水印] [--denoise 0.5] [--size 512]

说明：与「去水印.bat」（点阵层精确扣除）不同，本工具是 AI 重绘路线，
      效果接近豆包等在线 AI 的去水印结果；重绘程度由 --denoise 控制
      （0.4 更接近原图，0.6 更彻底但改动更大）。
"""
import argparse, io, json, os, sys, time, urllib.parse, urllib.request

import numpy as np
from PIL import Image

SERVER = 'http://127.0.0.1:8188'
CKPT = 'v1-5-pruned-emaonly.safetensors'
POS = ('a round enamel pin badge, intricate engraved metal artwork, clean product photo, '
       'sharp details, high quality, studio lighting')
NEG = ('watermark, text, letters, logo, tiled pattern, diagonal lines, dots, grid, '
       'faint marks, overlay, blurry, low quality, jpeg artifacts')


def upload_image(path, name):
    boundary = '----koutuai'
    with open(path, 'rb') as f:
        data = f.read()
    body = b''
    body += ('--%s\r\n' % boundary).encode()
    body += ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % name).encode()
    body += b'Content-Type: image/png\r\n\r\n' + data + b'\r\n'
    body += ('--%s\r\n' % boundary).encode()
    body += b'Content-Disposition: form-data; name="type"\r\n\r\ninput\r\n'
    body += ('--%s--\r\n' % boundary).encode()
    req = urllib.request.Request(SERVER + '/upload/image', data=body,
                                 headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())['name']


def build_workflow(img_name, size, denoise, seed):
    return {
        '2': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': CKPT}},
        '1': {'class_type': 'LoadImage', 'inputs': {'image': img_name}},
        '3': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['1', 0], 'vae': ['2', 2]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'text': POS, 'clip': ['2', 1]}},
        '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': NEG, 'clip': ['2', 1]}},
        '4': {'class_type': 'KSampler', 'inputs': {
            'seed': seed, 'steps': 28, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m',
            'scheduler': 'karras', 'denoise': denoise, 'model': ['2', 0],
            'positive': ['5', 0], 'negative': ['6', 0], 'latent_image': ['3', 0]}},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['4', 0], 'vae': ['2', 2]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'filename_prefix': 'koutu_ai', 'images': ['7', 0]}},
    }


def run_prompt(workflow, timeout_s=600):
    req = urllib.request.Request(SERVER + '/prompt',
                                 data=json.dumps({'prompt': workflow}).encode(),
                                 headers={'Content-Type': 'application/json'})
    pid = json.loads(urllib.request.urlopen(req, timeout=60).read())['prompt_id']
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        with urllib.request.urlopen(SERVER + '/history/' + pid, timeout=60) as r:
            hist = json.loads(r.read())
        if pid in hist:
            st = hist[pid]['status']
            if not st.get('completed'):
                raise RuntimeError('ComfyUI 失败: %s' % st.get('status_str'))
            out = None
            for v in hist[pid].get('outputs', {}).values():
                for im in v.get('images', []):
                    out = im['filename']
            return out
        time.sleep(1.5)
    raise TimeoutError('ComfyUI 超时')


def fetch_image(name):
    u = SERVER + '/view?filename=' + urllib.parse.quote(name) + '&type=output'
    with urllib.request.urlopen(u, timeout=120) as r:
        return Image.open(io.BytesIO(r.read())).convert('RGB')


def process(path, out_path, size, denoise):
    src = Image.open(path).convert('RGBA')
    W0, H0 = src.size
    # 白底合成 → 等比放大到 size（保持比例，补白）
    bg = Image.new('RGB', src.size, (255, 255, 255))
    bg.paste(src, mask=src.split()[3])
    scale = size / float(max(W0, H0))
    w1, h1 = int(round(W0 * scale)), int(round(H0 * scale))
    up = bg.resize((w1, h1), Image.LANCZOS)
    canvas = Image.new('RGB', (size, size), (255, 255, 255))
    ox, oy = (size - w1) // 2, (size - h1) // 2
    canvas.paste(up, (ox, oy))
    tmp = os.path.join(os.environ['TEMP'], '_koutu_ai_in.png')
    canvas.save(tmp)
    name = upload_image(tmp, '_koutu_ai_in.png')
    import zlib
    seed = zlib.crc32(open(path, 'rb').read()) % 1000000
    wf = build_workflow(name, size, denoise, seed=seed)
    out_name = run_prompt(wf)
    got = fetch_image(out_name)
    # 裁回并按原尺寸缩放
    back = got.crop((ox, oy, ox + w1, oy + h1)).resize((W0, H0), Image.LANCZOS)
    res = back.convert('RGBA')
    res.putalpha(src.split()[3])
    res.save(out_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description='本地 AI 去水印（ComfyUI img2img 重绘）')
    ap.add_argument('--src', default='底图')
    ap.add_argument('--dst', default='无水印')
    ap.add_argument('--size', type=int, default=512)
    ap.add_argument('--denoise', type=float, default=0.65)
    args = ap.parse_args(argv)
    root = os.path.dirname(os.path.abspath(__file__))
    src_dir = args.src if os.path.isabs(args.src) else os.path.join(root, args.src)
    dst_dir = args.dst if os.path.isabs(args.dst) else os.path.join(root, args.dst)
    os.makedirs(dst_dir, exist_ok=True)
    files = [f for f in sorted(os.listdir(src_dir))
             if os.path.splitext(f)[1].lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}]
    if not files:
        print('「%s」里没有图片。' % src_dir)
        return 1
    print('输入：%s\n输出：%s\ndenoise=%.2f size=%d' % (src_dir, dst_dir, args.denoise, args.size))
    print('-' * 66)
    ok = 0
    for f in files:
        try:
            out_path = os.path.join(dst_dir, os.path.splitext(f)[0] + '.png')
            t0 = time.time()
            process(os.path.join(src_dir, f), out_path, args.size, args.denoise)
            ok += 1
            print('%-16s 完成 (%.0f 秒)' % (f, time.time() - t0))
        except Exception as e:
            print('%-16s 失败：%s' % (f, e))
    print('-' * 66)
    print('完成：%d / %d，结果在「%s」' % (ok, len(files), os.path.basename(dst_dir)))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
