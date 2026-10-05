# -*- coding: utf-8 -*-
"""
去水印工具（重复平铺的淡色小字层去除）
======================================
作用：把「底图」文件夹里每张图片上的一层“重复平铺的淡色小字/细纹”水印
（约 13px 的小字符，按约 27px 的方格斜向铺满全图，亮度只比周围高几个色阶，
几乎看不清）整层找到并去掉，结果以同名 PNG 保存到「无水印」文件夹（保留透明通道）。

用法：双击「去水印.bat」，或：
    python remove_watermark.py [--src 底图] [--dst 无水印] [--pitch 27] [--preview]

原理：
    1. 用印记形模板在残差域做匹配滤波，检出清晰的水印印记；
    2. 由这些印记拟合铺排间距与相位（约 27px 方格），自动校核峰值显著性；
    3. 平滑区域按实测笔画逐处扣除，纹理区域按格点用稳健平均幅度扣除；
    4. 只改像素值，透明通道原样保留。
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

IMG_EXT = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.gif'}
TSZ = 21            # 点模板尺寸
SIGMA = 4.4         # 点形（高斯圆点）标准差
PITCH = 27.0        # 点阵间距（像素）
AMP_MIN, AMP_MAX = 1.0, 16.0    # 单点扣除幅度范围（灰度级）
TOTAL_CAP = 18.0    # 单像素最大扣除量


def to_gray(img):
    return np.asarray(img.convert('L')).astype(np.float64)


def gaussian(size, sigma):
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size]
    g = np.exp(-((xx - c) ** 2 + (yy - c) ** 2) / (2.0 * sigma * sigma))
    return g / g.max()


def median_f(arr, r):
    u8 = np.clip(arr, 0, 255).astype(np.uint8)
    return np.asarray(Image.fromarray(u8).filter(ImageFilter.MedianFilter(r))).astype(np.float64)


def _fft_corr(res, tpl):
    h, w = res.shape
    th, tw = tpl.shape
    Tp = np.zeros_like(res)
    Tp[:th, :tw] = tpl
    c = np.real(np.fft.ifft2(np.fft.fft2(res) * np.conj(np.fft.fft2(Tp))))
    out = np.zeros_like(res)
    out[:h - th + 1, :w - tw + 1] = c[:h - th + 1, :w - tw + 1]
    return out


def _center(arr, th, tw):
    """相关/统计图是“左上角索引”，转成“模板中心索引”（否则位置会整体偏移半个模板）"""
    h, w = arr.shape
    oy, ox = (th - 1) // 2, (tw - 1) // 2
    out = np.zeros((h, w))
    hh = h - th + 1
    ww = w - tw + 1
    out[oy:oy + hh, ox:ox + ww] = arr[:hh, :ww]
    return out


def _win_stats(res, th, tw):
    h, w = res.shape
    S1 = np.zeros((h + 1, w + 1))
    S2 = np.zeros((h + 1, w + 1))
    S1[1:, 1:] = np.cumsum(np.cumsum(res, 0), 1)
    S2[1:, 1:] = np.cumsum(np.cumsum(res * res, 0), 1)

    def win(S):
        return S[th:, tw:] - S[:-th, tw:] - S[th:, :-tw] + S[:-th, :-tw]

    n = th * tw
    m = win(S1) / n
    v = np.maximum(win(S2) / n - m * m, 0.0)
    full_m = np.zeros((h, w))
    full_s = np.zeros((h, w))
    full_m[:h - th + 1, :w - tw + 1] = m
    full_s[:h - th + 1, :w - tw + 1] = np.sqrt(v)
    return _center(full_m, th, tw), _center(full_s, th, tw)


def ncc_map(res, tpl):
    th, tw = tpl.shape
    T0 = tpl - tpl.mean()
    c = _center(_fft_corr(res, T0), th, tw)
    m, s = _win_stats(res, th, tw)
    num = c - m * T0.sum()
    den = s * (th * tw) * np.sqrt((T0 ** 2).mean()) + 1e-9
    return num / den


def amp_map(res, tpl):
    """每一点作为“模板中心”处的幅度（最小二乘拟合值）"""
    T0 = tpl - tpl.mean()
    c = _fft_corr(res, T0) / ((T0 ** 2).sum() + 1e-9)
    return _center(c, tpl.shape[0], tpl.shape[1])


def find_peaks(ncc, thr):
    """ncc 已按“中心索引”，峰值坐标即模板中心坐标"""
    pts = []
    off = (TSZ - 1) // 2
    hh, ww = ncc.shape
    for y in range(off + 1, hh - off - 1):
        row = ncc[y]
        up = ncc[y - 1]
        dn = ncc[y + 1]
        for x in range(off + 1, ww - off - 1):
            v = row[x]
            if v > thr and v >= row[x - 1] and v >= row[x + 1] and v >= up[x] and v >= dn[x]:
                pts.append((x, y, float(v)))
    return pts


def patch_at(arr, x, y, size=TSZ):
    off = (size - 1) // 2
    h, w = arr.shape[:2]
    if y - off < 0 or x - off < 0 or y + off >= h or x + off >= w:
        return None
    return arr[y - off:y + off + 1, x - off:x + off + 1]


def measure_shape(L, med, pts, ring, tpl_syn):
    """用部分检出点对齐平均，得到该图真实点形（峰值归一化为 1）"""
    res = L - med
    c = (TSZ - 1) / 2.0
    yy, xx = np.mgrid[0:TSZ, 0:TSZ]
    acc = np.zeros((TSZ, TSZ))
    n = 0
    for (x, y, sc) in sorted(pts, key=lambda q: -q[2])[:150]:
        p = patch_at(res, x, y)
        if p is None:
            continue
        if float(p[ring].std()) > 2.5:
            continue
        wgt = np.clip(p - np.median(p), 0, None)
        if wgt.sum() < 5:
            continue
        cy = float((wgt * yy).sum() / wgt.sum())
        cx = float((wgt * xx).sum() / wgt.sum())
        sy = int(round(c - cy))
        sx = int(round(c - cx))
        if abs(sy) > 3 or abs(sx) > 3:
            continue
        acc += np.roll(np.roll(p, sy, 0), sx, 1)
        n += 1
    if n < 10:
        return None
    sh = acc / n
    sh = sh - np.median(sh)
    sh = np.clip(sh, 0, None)
    if sh.max() < 1.0:
        return None
    return sh / sh.max()


def phase_search(amps, opaque, pitch):
    """在相位空间搜索点阵：不透明区域格点处平均幅度最大的相位，
    并要求该峰值明显高于其他相位（避免锁到噪声）"""
    h, w = amps.shape
    R = int(round(pitch))
    scores = []
    for px in range(R):
        xs = np.arange(px, w - 1, pitch).astype(int)
        if len(xs) < 4:
            continue
        for py in range(R):
            ys = np.arange(py, h - 1, pitch).astype(int)
            if len(ys) < 4:
                continue
            X, Y = np.meshgrid(xs, ys)
            m = opaque[Y, X]
            if m.sum() < 20:
                continue
            scores.append((float(amps[Y, X][m].mean()), px, py, int(m.sum())))
    if not scores:
        return None
    scores.sort(key=lambda s: -s[0])
    best = scores[0]
    others = np.array([s[0] for s in scores[1:]])
    if not len(others):
        return None
    if best[0] >= 1.5 and (best[0] - float(np.percentile(others, 90))) >= 0.6:
        return best
    return None


def process_image(path, pitch):
    src = Image.open(path)
    rgba = src.convert('RGBA')
    rgb = np.asarray(rgba.convert('RGB')).astype(np.float64)
    alpha = np.asarray(rgba)[..., 3].astype(np.float64)
    L = to_gray(rgba)
    stats = {'dots': 0, 'removed': 0, 'amp_p50': 0.0, 'max_delta': 0.0,
             'mean_delta': 0.0, 'phase': None, 'amp_before': 0.0, 'amp_after': 0.0}
    if min(L.shape) < 3 * TSZ:
        return rgba, stats

    med = median_f(L, 21)
    res = L - med
    shape = gaussian(TSZ, SIGMA)
    tpl = shape - shape.mean()
    ring = shape < 0.06

    pts0 = find_peaks(ncc_map(res, tpl), 0.45)
    meas = measure_shape(L, med, pts0, ring, tpl)
    if meas is not None:
        shape = meas
        tpl = shape - shape.mean()
        ring = shape < 0.06

    h, w = L.shape
    off = (TSZ - 1) // 2
    amps = amp_map(res, tpl)
    _, noise = _win_stats(res, TSZ, TSZ)
    pts = find_peaks(ncc_map(res, tpl), 0.45)
    stats['dots'] = len(pts)

    ps = phase_search(amps, alpha > 0.5, pitch)
    corr = np.zeros_like(L)
    used = []
    if ps is not None:
        score, px, py, nsel = ps
        stats['phase'] = (px, py)
        stats['amp_before'] = float(score)
        grid_amps = []
        for x in np.arange(px, w - 1, pitch):
            for y in np.arange(py, h - 1, pitch):
                xi, yi = int(round(x)), int(round(y))
                a = float(amps[yi, xi])
                if float(noise[yi, xi]) < 3.0 and AMP_MIN <= a <= AMP_MAX:
                    grid_amps.append(a)
        pos = [a for a in grid_amps if a > 2.0]
        med_amp = float(score)
        if len(pos) >= 8:
            med_amp = float(np.median(pos))
        for x in np.arange(px, w - 1, pitch):
            for y in np.arange(py, h - 1, pitch):
                xi, yi = int(round(x)), int(round(y))
                if xi - off < 0 or yi - off < 0 or xi + off + 1 > w or yi + off + 1 > h:
                    continue
                a = float(amps[yi, xi])
                ns = float(noise[yi, xi])
                if ns < 3.0 and AMP_MIN <= a <= AMP_MAX:
                    # 平滑区域：直接按实测笔画扣除（含本处字形细节，更彻底）
                    p0 = patch_at(res, xi, yi)
                    up = np.clip(p0 + 128, 0, 255).astype(np.uint8)
                    sub = np.asarray(Image.fromarray(up).filter(
                        ImageFilter.GaussianBlur(0.8))).astype(np.float64) - 128.0
                    sub = np.clip(sub, 0.0, TOTAL_CAP)
                    corr[yi - off:yi + off + 1, xi - off:xi + off + 1] += sub
                    used.append(a)
                else:
                    amp = min(max(med_amp, 1.5), TOTAL_CAP)
                    corr[yi - off:yi + off + 1, xi - off:xi + off + 1] += amp * shape
                    used.append(amp)
    else:
        for (x, y, sc) in pts:
            p = patch_at(res, x, y)
            if p is None:
                continue
            amp = float((p * tpl).sum() / ((tpl ** 2).sum() + 1e-9))
            ns = float(p[ring].std())
            if not (AMP_MIN <= amp <= AMP_MAX) or amp < 4.0 * max(ns, 0.5):
                continue
            corr[y - off:y + off + 1, x - off:x + off + 1] += amp * shape
            used.append(amp)

    corr = np.clip(corr, 0.0, TOTAL_CAP)
    corr = corr * (alpha > 0.5)
    out = np.clip(rgb - corr[..., None], 0, 255)
    res_img = np.dstack([out, alpha]).astype(np.uint8)

    if stats['phase'] is not None:
        px, py = stats['phase']
        L2 = out.mean(-1)
        med2 = median_f(L2, 21)
        amps2 = amp_map(L2 - med2, tpl)
        after = []
        for x in np.arange(px, w - 1, pitch):
            for y in np.arange(py, h - 1, pitch):
                xi, yi = int(round(x)), int(round(y))
                if float(noise[yi, xi]) < 3.0:
                    after.append(float(amps2[yi, xi]))
        if after:
            stats['amp_after'] = float(np.mean(after))

    diff = np.abs(out - rgb).max(-1)
    op = alpha > 0
    stats['removed'] = len(used)
    stats['amp_p50'] = float(np.median(used)) if used else 0.0
    stats['max_delta'] = float(diff.max()) if diff.size else 0.0
    stats['mean_delta'] = float(diff[op].mean()) if op.any() else float(diff.mean())
    return Image.fromarray(res_img, 'RGBA'), stats


def save_preview(src_path, out_img, dst_dir, name):
    """放大 + 增强的对比图（左原件 / 右处理后）"""
    src = Image.open(src_path).convert('RGBA')
    a = np.asarray(src.convert('RGB')).astype(np.float64)
    b = np.asarray(out_img.convert('RGB')).astype(np.float64)
    h, w = a.shape[:2]
    step = max(1, min(w, h) // 200)
    a = a[::step, ::step]
    b = b[::step, ::step]

    def boost(p):
        return np.clip((p - p.mean()) * 5 + 128, 0, 255).astype(np.uint8)

    left = boost(a)
    right = boost(b)
    sep = np.full((left.shape[0], 4, 3), 255, np.uint8)
    canvas = np.concatenate([left, sep, right], 1)
    os.makedirs(dst_dir, exist_ok=True)
    Image.fromarray(canvas).save(os.path.join(dst_dir, '对比_%s.png' % name))


def main(argv=None):
    ap = argparse.ArgumentParser(description='点阵水印自动去除')
    ap.add_argument('--src', default='底图', help='输入目录（默认：底图）')
    ap.add_argument('--dst', default='无水印', help='输出目录（默认：无水印）')
    ap.add_argument('--pitch', type=float, default=PITCH, help='点阵间距，像素（默认 27）')
    ap.add_argument('--preview', action='store_true', help='生成 去水印_预览/ 对比图')
    args = ap.parse_args(argv)

    root = os.path.dirname(os.path.abspath(__file__))
    src_dir = args.src if os.path.isabs(args.src) else os.path.join(root, args.src)
    dst_dir = args.dst if os.path.isabs(args.dst) else os.path.join(root, args.dst)
    os.makedirs(dst_dir, exist_ok=True)

    files = [f for f in sorted(os.listdir(src_dir))
             if os.path.splitext(f)[1].lower() in IMG_EXT]
    if not files:
        print('「%s」里没有可处理的图片。' % src_dir)
        return 1

    print('输入：%s' % src_dir)
    print('输出：%s' % dst_dir)
    print('-' * 78)
    ok = 0
    for f in files:
        p = os.path.join(src_dir, f)
        try:
            out_img, st = process_image(p, args.pitch)
            out_img.save(os.path.join(dst_dir, os.path.splitext(f)[0] + '.png'))
            ok += 1
            ph = st['phase']
            drop = 0.0
            if st['amp_before'] > 1e-6:
                drop = 100.0 * (1 - st['amp_after'] / st['amp_before'])
            print('%-16s 格点 %4d 处  相位 %-9s  点幅度 %.1f -> %.1f (降 %.0f%%)  最大改动 %.0f 级' % (
                f, st['removed'], ('(%d,%d)' % ph) if ph else '逐点模式',
                st['amp_before'], st['amp_after'], drop, st['max_delta']))
            if args.preview:
                save_preview(p, out_img, os.path.join(root, '去水印_预览'), os.path.splitext(f)[0])
        except Exception as e:  # noqa
            print('%-16s 处理失败：%s' % (f, e))
    print('-' * 78)
    print('完成：成功 %d / %d 张，结果在「%s」。' % (ok, len(files), os.path.basename(dst_dir)))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
