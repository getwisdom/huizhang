"""水印去除原型 v1（W3.3）：相位折叠模板扣除（选型 A）。

流程（确定性，无随机）：
1) 观测区 = alpha==0；残差 = 亮度 − 中值21；
2) 角区自相关亚像素峰定基（research7.estimate_basis）；基合理性门槛（长度 23–29px、夹角 83–97°）；
3) 折叠（26×26 / 13×13 半阶两口径）相位搜索（0.05 粗搜 + 0.01 精修）；
4) 模板 = 观测区折叠格均值（可选循环高斯平滑）；
5) 幅度 k = 观测区最小二乘拟合（夹取 0–1.5），对全图 RGB 等量扣除、0–255 夹取、alpha 不动；
6) 指标：观测区幅度降幅（留一角法）、全图/徽章面改动量级、伪影（扣除后折叠结构回落）；
7) 样张：每张一份对照图（前后/差分/角区残差放大），写 spike/_out/w3-3-samples/。

门槛（初定，W3.4 定稿）：无合理基 或 26 口径折叠结构 <1.4σ → 判定「不可观测」→ 不扣除（输出=输入副本）。
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

from research7 import BASE, load_luma_alpha, med, corner_big, estimate_basis, fold_cell

NAMES = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "测试_1.png"]
OUT = BASE.parents[2] / "spike" / "_out" / "w3-3-samples"
C = 48
MIN_PITCH, MAX_PITCH = 23.0, 29.0
MIN_ANGLE, MAX_ANGLE = 83.0, 97.0
SIG_GATE = 1.4


def find_phase(res, m0, b1, b2, n):
    best = None
    for p1 in np.arange(0, 1, 0.05):
        for p2 in np.arange(0, 1, 0.05):
            cell, _ = fold_cell(res, m0, b1, b2, (p1, p2), n, n)
            v = float(np.var(cell))
            if best is None or v > best[0]:
                best = (v, p1, p2)
    _, q1, q2 = best
    for p1 in np.arange(q1 - 0.04, q1 + 0.041, 0.01):
        for p2 in np.arange(q2 - 0.04, q2 + 0.041, 0.01):
            cell, _ = fold_cell(res, m0, b1, b2, (p1, p2), n, n)
            v = float(np.var(cell))
            if v > best[0]:
                best = (v, p1, p2)
    return best[1], best[2]


def smooth_cell(cell, sigma_units):
    if sigma_units <= 0:
        return cell
    n = cell.shape[0]
    fu = np.fft.fftfreq(n)[None, :]
    fv = np.fft.fftfreq(n)[:, None]
    g = np.exp(-2 * (np.pi ** 2) * (sigma_units ** 2) * (fu ** 2 + fv ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(cell) * g))


def template_field(shape, b1, b2, phase, n, cell):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    inv = np.linalg.inv(np.array([b1, b2]))
    coords = np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float64)
    uv = coords @ inv.T - np.array(phase)
    fu = uv[:, 0] - np.floor(uv[:, 0])
    fv = uv[:, 1] - np.floor(uv[:, 1])
    bi = np.clip((fv * n).astype(int), 0, n - 1)
    bj = np.clip((fu * n).astype(int), 0, n - 1)
    return cell[bi, bj].reshape(h, w)


def lsq_k(res, mask, tfield):
    r = res[mask]
    t = tfield[mask]
    den = float(np.sum(t * t))
    if den < 1e-9:
        return 0.0
    return float(np.sum(r * t) / den)


def corners(h, w):
    return {
        "TL": (slice(0, C), slice(0, C)),
        "TR": (slice(0, C), slice(w - C, w)),
        "BL": (slice(h - C, h), slice(0, C)),
        "BR": (slice(h - C, h), slice(w - C, w)),
    }


def loo_reduction(res, m0, b1, b2, phase, n, sigma):
    reds = []
    for key, (sy, sx) in corners(*res.shape).items():
        cm = np.zeros_like(m0)
        cm[sy, sx] = True
        train = m0 & ~cm
        if train.sum() < 2000 or cm.sum() < 500:
            continue
        cell, _ = fold_cell(res, train, b1, b2, phase, n, n)
        cell = cell - cell.mean()
        cell = smooth_cell(cell, sigma)
        tf = template_field(res.shape, b1, b2, phase, n, cell)
        r = res[cm]
        if float(np.std(r)) < 0.05:
            continue
        k = float(np.sum(r * tf[cm]) / max(float(np.sum(tf[cm] ** 2)), 1e-9))
        k = float(np.clip(k, 0.0, 1.5))
        after = r - k * tf[cm]
        reds.append(1.0 - float(np.std(after)) / max(float(np.std(r)), 1e-9))
    return float(np.mean(reds)) if reds else float("nan")


def build_sheet(name, rgba_before, rgba_after, res_before, res_after, m0, out_dir):
    before = Image.fromarray(rgba_before.astype(np.uint8), "RGBA").convert("RGB")
    after = Image.fromarray(rgba_after.astype(np.uint8), "RGBA").convert("RGB")
    d = np.abs(rgba_after[..., :3].astype(np.float32) - rgba_before[..., :3].astype(np.float32)).max(2)
    d8 = np.clip(d * 32, 0, 255).astype(np.uint8)
    diff = Image.fromarray(np.stack([d8] * 3, -1), "RGB")
    h, w = res_before.shape

    def res_panel(res, y0, y1, x0, x1, scale=3):
        blk = np.clip((res[y0:y1, x0:x1] + 3.0) / 6.0 * 255, 0, 255).astype(np.uint8)
        im = Image.fromarray(np.stack([blk] * 3, -1), "RGB")
        return im.resize((im.width * scale, im.height * scale), Image.NEAREST)

    sy, sx = corners(h, w)["TL"]
    rp_b = res_panel(res_before, sy.start, sy.start + 96, sx.start, sx.start + 96)
    rp_a = res_panel(res_after, sy.start, sy.start + 96, sx.start, sx.start + 96)
    margin = 12
    width = before.width * 3 + margin * 4
    height = before.height + rp_b.height + margin * 3
    sheet = Image.new("RGB", (width, height), (40, 40, 40))
    x = margin
    sheet.paste(before, (x, margin)); x += before.width + margin
    sheet.paste(after, (x, margin)); x += after.width + margin
    sheet.paste(diff, (x, margin))
    sheet.paste(rp_b, (margin, before.height + margin * 2))
    sheet.paste(rp_a, (margin * 2 + rp_b.width, before.height + margin * 2))
    out = out_dir / f"{Path(name).stem}_对照.png"
    sheet.save(out)
    return out


def _emit_skip(name, lines):
    rgb = np.asarray(Image.open(BASE / name).convert("RGBA")).astype(np.float32)
    L2 = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    res = L2 - med(L2, 21)
    m0 = rgb[..., 3] == 0
    out = rgb.astype(np.uint8)
    Image.fromarray(out, "RGBA").save(OUT / name)
    sheet = build_sheet(name, out, out, res, res, m0, OUT)
    lines.append(f"  样张: {sheet}（前后一致，未扣除）")


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else NAMES
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    for name in names:
        L, alpha = load_luma_alpha(BASE / name)
        h, w = L.shape
        res = L - med(L, 21)
        m0 = alpha == 0
        lines.append(f"===== {name} =====")
        big, bmask = corner_big(res)
        basis, _ = estimate_basis(big, bmask)
        ok = False
        if len(basis) == 2:
            b1v, b2v = basis
            l1, l2 = np.hypot(*b1v), np.hypot(*b2v)
            ang = np.degrees(np.arccos(np.clip(np.dot(b1v, b2v) / (l1 * l2), -1, 1)))
            ok = MIN_PITCH <= l1 <= MAX_PITCH and MIN_PITCH <= l2 <= MAX_PITCH and MIN_ANGLE <= ang <= MAX_ANGLE
            lines.append(f"  基 b1=({b1v[0]:.3f},{b1v[1]:.3f}) b2=({b2v[0]:.3f},{b2v[1]:.3f}) |b|={l1:.2f},{l2:.2f} 夹角={ang:.1f}° 门槛={'过' if ok else '不过'}")
        if not ok:
            lines.append("  [判定] 不可观测（无合理基）→ 不扣除")
            _emit_skip(name, lines)
            continue
        # 26 口径门禁 + 两口径相位
        p26 = find_phase(res, m0, b1v, b2v, 26)
        cell26, cnt26 = fold_cell(res, m0, b1v, b2v, p26, 26, 26)
        sig26 = float(np.std(cell26)) / max(1e-9, float(res[m0].std()) / np.sqrt(cnt26.mean()))
        p13 = find_phase(res, m0, (b1v[0] / 2, b1v[1] / 2), (b2v[0] / 2, b2v[1] / 2), 13)
        if sig26 < SIG_GATE:
            lines.append(f"  [判定] 26 口径折叠 {sig26:.2f}σ < 门禁 {SIG_GATE} → 不可观测 → 不扣除")
            _emit_skip(name, lines)
            continue
        # 两口径 × 平滑档的留一法评估（选择用）
        cands = []
        for tag, n, bb1, bb2, ph in [
            ("26", 26, b1v, b2v, p26),
            ("13", 13, (b1v[0] / 2, b1v[1] / 2), (b2v[0] / 2, b2v[1] / 2), p13),
        ]:
            for sigma in (0.0, 1.0, 1.5):
                red = loo_reduction(res, m0, bb1, bb2, ph, n, sigma)
                cands.append((red, tag, n, bb1, bb2, ph, sigma))
                lines.append(f"  留一法评估[{tag}px σ={sigma}]: 幅度降幅={red*100:.1f}%")
        cands.sort(key=lambda t: (-t[0], t[1], t[6]))
        red, tag, n, bb1, bb2, ph, sigma = cands[0]
        lines.append(f"  [选择] 口径={tag}px σ={sigma} 留一降幅={red*100:.1f}%")
        # 最终模板（全观测区）
        cell, cnt = fold_cell(res, m0, bb1, bb2, ph, n, n)
        cell = cell - cell.mean()
        cell = smooth_cell(cell, sigma)
        tf = template_field((h, w), bb1, bb2, ph, n, cell)
        k = float(np.clip(lsq_k(res, m0, tf), 0.0, 1.5))
        rgb = np.asarray(Image.open(BASE / name).convert("RGBA")).astype(np.float32)
        delta = k * tf
        out_rgb = np.clip(np.rint(rgb[..., :3] - delta[..., None]), 0, 255).astype(np.uint8)
        out_rgba = np.concatenate([out_rgb, rgb[..., 3:4].astype(np.uint8)], axis=2)
        # 指标
        after_res = (out_rgb.astype(np.float32).mean(2)) - med(out_rgb.astype(np.float32).mean(2), 21)
        obs_after = after_res[m0]
        d_all = np.abs(out_rgb.astype(np.float32) - rgb[..., :3]).max(2)
        mbadge = alpha > 240
        d_badge = d_all[mbadge]
        cellA, cntA = fold_cell(after_res, m0, bb1, bb2, ph, n, n)
        sigA = float(np.std(cellA)) / max(1e-9, float(obs_after.std()) / np.sqrt(cntA.mean()))
        lines.append(f"  幅度 k={k:.3f} | 观测区std {res[m0].std():.2f}→{obs_after.std():.2f} | 折叠σ {sig26 if tag=='26' else float('nan'):.2f}(26)→{sigA:.2f}(扣除后,{tag})")
        lines.append(f"  改动 |Δ|: 全图 mean={d_all.mean():.3f} p99={np.percentile(d_all,99):.1f} max={d_all.max():.1f} 占(|Δ|≥1)={float((d_all>=1).mean())*100:.1f}% | 徽章面(α>240) mean={d_badge.mean():.3f} p99={np.percentile(d_badge,99):.1f} max={d_badge.max():.1f} 占(|Δ|≥1)={float((d_badge>=1).mean())*100:.1f}%")
        alpha_ok = bool((out_rgba[..., 3] == rgb[..., 3].astype(np.uint8)).all())
        lines.append(f"  alpha 逐像素一致: {alpha_ok}")
        Image.fromarray(out_rgba, "RGBA").save(OUT / name)
        sheet = build_sheet(name, rgb.astype(np.uint8), out_rgba, res, after_res, m0, OUT)
        lines.append(f"  样张: {sheet}")
    text = "\n".join(lines)
    print(text)
    (OUT / "指标表.txt").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
