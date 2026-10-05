# -*- coding: utf-8 -*-
"""
去水印工具（细纹压制版 / 三档强度）
====================================
底图里那层"重复平铺的细线/小字"是叠在画面上的细密纹理，
用中值滤波可以判掉细线、保住大结构；强度可分档：

    轻：结果 = 原图 + 0.35 x (中值 - 原图)   细纹降 ~30%，肉眼几乎不变
    中：结果 = 原图 + 0.65 x (中值 - 原图)   细纹降 ~55%，主体结构完好（推荐）
    重：结果 = 中值                           细纹降 ~85%，画面明显变干净/变软

只改亮度（水印是中性灰，三通道等量），保留透明通道。

用法：
    python detex.py [--src 底图] [--strength 中] [--preview]
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

IMG_EXT = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.gif'}
LEVELS = {'轻': 0.35, '中': 0.65, '重': 1.0}


def median_f(g, r):
    return np.asarray(Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
                      .filter(ImageFilter.MedianFilter(r))).astype(np.float64)


def load_rgb(path):
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im).astype(np.float64)
    rgb = a[..., :3]
    alpha = a[..., 3]
    return rgb, alpha


def run(src_dir, dst_dir, k, radius, preview_dir=None, zoom=3):
    os.makedirs(dst_dir, exist_ok=True)
    rows = []
    for f in sorted(os.listdir(src_dir)):
        if os.path.splitext(f)[1].lower() not in IMG_EXT:
            continue
        rgb, alpha = load_rgb(os.path.join(src_dir, f))
        L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        M = median_f(L, radius)
        L2 = L + k * (M - L)
        out = np.clip(rgb + (L2 - L)[..., None], 0, 255)
        img = Image.fromarray(np.dstack([out, alpha]).astype(np.uint8), 'RGBA')
        img.save(os.path.join(dst_dir, os.path.splitext(f)[0] + '.png'))

        op = alpha > 0
        d = np.abs(out - rgb).max(-1)
        # 细纹强度：最平坦的若干窗口里 (图 - 中值5) 的 σ
        noise = np.abs(L - median_f(L, 3))
        H, Wd = L.shape
        wins = []
        for y in range(0, max(H - 40, 1), 8):
            for x in range(0, max(Wd - 120, 1), 8):
                if op[y:y + 40, x:x + 120].mean() < 0.99:
                    continue
                wins.append((float(noise[y:y + 40, x:x + 120].mean()), x, y))
        wins.sort()
        wins = wins[:8]

        def line(g):
            v = []
            for _v, x, y in wins:
                S = g[y:y + 40, x:x + 120]
                v.append(float((S - median_f(S, 5)).std()))
            return float(np.mean(v)) if v else 0.0

        fine0, fine1 = line(L), line(L2)
        rows.append((f, float(d[op].mean()), float(np.percentile(d[op], 99)),
                     fine0, fine1, 100 * (1 - fine1 / max(fine0, 1e-6))))
        if preview_dir:
            a = np.asarray(Image.open(os.path.join(src_dir, f)).convert('RGB')).astype(np.float64)
            b = np.asarray(img.convert('RGB')).astype(np.float64)

            def boost(p):
                return np.clip((p - p.mean()) * 3 + 128, 0, 255).astype(np.uint8)

            lft = Image.fromarray(boost(a))
            rgt = Image.fromarray(boost(b))
            lft = lft.resize((lft.size[0] * zoom, lft.size[1] * zoom), Image.NEAREST)
            rgt = rgt.resize((rgt.size[0] * zoom, rgt.size[1] * zoom), Image.NEAREST)
            cv = Image.new('RGB', (lft.size[0] * 2 + 10, lft.size[1]), (255, 255, 255))
            cv.paste(lft, (0, 0))
            cv.paste(rgt, (lft.size[0] + 10, 0))
            os.makedirs(preview_dir, exist_ok=True)
            cv.save(os.path.join(preview_dir, '细纹对比_%s' % os.path.splitext(f)[0] + '.png'))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description='细纹压制去水印')
    ap.add_argument('--src', default='底图')
    ap.add_argument('--strength', default='中', choices=list(LEVELS.keys()))
    ap.add_argument('--radius', type=int, default=5, help='中值滤波半径（奇数，5 -> 5x5）')
    ap.add_argument('--preview', action='store_true')
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.abspath(__file__))
    src_dir = args.src if os.path.isabs(args.src) else os.path.join(root, args.src)
    k = LEVELS[args.strength]
    dst = os.path.join(root, '无水印' if args.strength == '中' else '无水印_细纹%s' % args.strength)
    pv = os.path.join(root, '去水印_预览') if args.preview else None
    print('输入：%s\n输出：%s\n强度：%s (k=%.2f)  中值半径=%d' % (src_dir, dst, args.strength, k, args.radius))
    print('-' * 92)
    rows = run(src_dir, dst, k, args.radius, pv)
    for f, dm, d99, f0, f1, drop in rows:
        print('%-16s 平均改动 %.2f 级 (99%%: %.1f)   细纹σ %.2f -> %.2f  (降 %.0f%%)' % (f, dm, d99, f0, f1, drop))
    print('-' * 92)
    print('完成：%d 张。' % len(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main())
