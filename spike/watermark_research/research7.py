"""水印域测绘 v8（W3.1）：7 张统计汇总 —— 间距 / 幅度 / 覆盖率。

沿用 research4/5/6 的既有方法（不重新推导）：
- 观测区 = alpha==0（圆外背景；跨图实测占比约 24–25%）；
- 残差 = 亮度 − 中值21（与 research4/5/6 一致）；
- 间距 = 四角拼接自相关亚像素峰（±26 邻域抛物线插值；候选基取最强两个非平行峰）；
- 幅度 = 观测区残差 std / p1 / p99 + 26×26 折叠字形峰谷（p98−p2）；
- 覆盖率 = ①观测区占比（alpha==0 面积比）②全幅铺排（四角联合折叠显著性）
  ③格内笔画覆盖率（|字形|≥1.0 灰度级的格点占比）。
- 13×13（半阶）折叠对照：判断字形是否为 2×2 子格结构。

输出为 UTF-8 文本；运行方式见 docs/水印研究.md（输出重定向到文件后读取）。
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def find_repo() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "koutu").is_dir() and (parent / "golden").is_dir():
            return parent
    raise RuntimeError("repo not found")


REPO = find_repo()
BASE = REPO / "golden" / "baseline_products" / "底图"
NAMES = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "测试_1.png"]
C = 48  # 角区观测块边长（与 research5/6 一致）


def load_luma_alpha(path: Path):
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    L = 0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]
    return L, rgba[..., 3]


def med(L: np.ndarray, size: int = 21) -> np.ndarray:
    u8 = np.clip(np.rint(L), 0, 255).astype(np.uint8)
    return np.asarray(
        Image.fromarray(u8, "L").filter(ImageFilter.MedianFilter(size))
    ).astype(np.float32)


def corners_mask(h: int, w: int, c: int = C) -> np.ndarray:
    m = np.zeros((h, w), dtype=bool)
    m[0:c, 0:c] = True
    m[0:c, w - c : w] = True
    m[h - c : h, 0:c] = True
    m[h - c : h, w - c : w] = True
    return m


def corner_big(res: np.ndarray, c: int = C) -> np.ndarray:
    """四角拼成 2×2 等效大图（4px 间隔），与 research5 一致。"""
    h, w = res.shape
    big = np.zeros((2 * c + 4, 2 * c + 4), dtype=np.float32)
    big[0:c, 0:c] = res[0:c, 0:c]
    big[0:c, c + 4 : 2 * c + 4] = res[0:c, w - c : w]
    big[c + 4 : 2 * c + 4, 0:c] = res[h - c : h, 0:c]
    big[c + 4 : 2 * c + 4, c + 4 : 2 * c + 4] = res[h - c : h, w - c : w]
    m = np.zeros_like(big, dtype=bool)
    m[0:c, 0:c] = True
    m[0:c, c + 4 : 2 * c + 4] = True
    m[c + 4 : 2 * c + 4, 0:c] = True
    m[c + 4 : 2 * c + 4, c + 4 : 2 * c + 4] = True
    return big, m


def subpixel_peak(A: np.ndarray, cx: int, cy: int, dx0: int, dy0: int):
    z0 = A[cy + dy0, cx + dx0]
    zx1 = A[cy + dy0, cx + dx0 + 1]
    zx0 = A[cy + dy0, cx + dx0 - 1]
    zy1 = A[cy + dy0 + 1, cx + dx0]
    zy0 = A[cy + dy0 - 1, cx + dx0]

    def parab(zm, z0_, zp):
        den = zm - 2 * z0_ + zp
        if abs(den) < 1e-9 or den > 0:
            return 0.0
        return float(np.clip(0.5 * (zm - zp) / den, -1.0, 1.0))

    return dx0 + parab(zx0, z0, zx1), dy0 + parab(zy0, z0, zy1), z0


def autocorr(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    F = np.fft.fft2((a - a[mask].mean()) * mask)
    return np.fft.fftshift(np.abs(np.fft.ifft2(F * np.conj(F))).real)


def fold_cell(res, mask, b1, b2, phase, n1, n2):
    Bm = np.array([b1, b2])
    invB = np.linalg.inv(Bm)
    ys, xs = np.nonzero(mask)
    coords = np.stack([xs, ys], 1).astype(np.float64)
    uv = coords @ invB.T - np.array(phase)
    fu = uv[:, 0] - np.floor(uv[:, 0])
    fv = uv[:, 1] - np.floor(uv[:, 1])
    bu = np.clip((fu * n1).astype(int), 0, n1 - 1)
    bv = np.clip((fv * n2).astype(int), 0, n2 - 1)
    cs = np.zeros((n2, n1))
    cc = np.zeros((n2, n1))
    np.add.at(cs, (bv, bu), res[ys, xs])
    np.add.at(cc, (bv, bu), 1.0)
    return cs / np.maximum(cc, 1), cc


def best_phase(res, mask, b1, b2, n1, n2, steps=20):
    best = None
    for p1 in np.arange(0, 1, 1.0 / steps):
        for p2 in np.arange(0, 1, 1.0 / steps):
            cell, _ = fold_cell(res, mask, b1, b2, (p1, p2), n1, n2)
            v = float(np.var(cell))
            if best is None or v > best[0]:
                best = (v, p1, p2)
    return best


def estimate_basis(big: np.ndarray, bmask: np.ndarray):
    """自相关 ±26 邻域亚像素峰 → 取最强两个非平行峰为基。"""
    A = autocorr(big, bmask)
    cy = cx = big.shape[0] // 2
    cand = []
    for dx0, dy0 in [
        (26, 0), (25, 0), (27, 0), (0, 26), (0, 25), (0, 27),
        (26, 1), (25, 1), (1, 26), (1, 25), (26, -1), (25, -1),
        (-1, 26), (-1, 25), (26, -2), (25, -2), (2, 26), (2, 25),
    ]:
        dx, dy, z = subpixel_peak(A, cx, cy, dx0, dy0)
        cand.append((z, dx, dy))
    cand.sort(key=lambda t: -t[0])
    basis = []
    for z, dx, dy in cand:
        v = np.array([dx, dy], float)
        if abs(v[1]) < 5 and v[0] < 0:
            continue
        if abs(v[0]) < 5 and v[1] < 0:
            continue
        if all(abs(v[0] * b[1] - v[1] * b[0]) > 200 for b in basis):
            basis.append(v)
        if len(basis) == 2:
            break
    return basis, cand


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else NAMES
    shared = None
    for name in names:
        L, alpha = load_luma_alpha(BASE / name)
        h, w = L.shape
        res = L - med(L, 21)
        m0 = alpha == 0
        big, bmask = corner_big(res)
        basis, cand = estimate_basis(big, bmask)
        obs = res[m0]
        print(f"===== {name}  {w}x{h}  观测区(alpha=0)={m0.mean()*100:.1f}% =====")
        print(f"  观测区残差: std={obs.std():.2f} p1={np.percentile(obs,1):.2f} p99={np.percentile(obs,99):.2f}")
        if len(basis) < 2:
            print("  [角区自相关] 未能定基（角区被内容占据）")
            continue
        b1v, b2v = basis
        print(f"  角区自相关峰（前6，亚像素）:")
        for z, dx, dy in cand[:6]:
            print(f"    (dx={dx:+.3f}, dy={dy:+.3f}) |v|={np.hypot(dx,dy):.3f} 峰值={z:.3e}")
        print(f"  [角区基] b1=({b1v[0]:.3f},{b1v[1]:.3f}) b2=({b2v[0]:.3f},{b2v[1]:.3f})  "
              f"|b1|={np.hypot(*b1v):.3f} |b2|={np.hypot(*b2v):.3f}  "
              f"夹角={np.degrees(np.arccos(np.clip(np.dot(b1v,b2v)/(np.hypot(*b1v)*np.hypot(*b2v)),-1,1))):.1f}°")
        # 26×26 折叠（α=0 观测区，相位粗搜）
        v26, p1, p2 = best_phase(res, m0, b1v, b2v, 26, 26, 20)
        cell26, cnt26 = fold_cell(res, m0, b1v, b2v, (p1, p2), 26, 26)
        noise = obs.std() / np.sqrt(max(1.0, cnt26.mean()))
        sig26 = float(np.std(cell26)) / max(1e-9, noise)
        apex = float(np.percentile(cell26, 98) - np.percentile(cell26, 2))
        ink = float((np.abs(cell26) >= 1.0).mean())
        print(f"  [26×26 折叠] 相位=({p1:.2f},{p2:.2f}) 样本/格={cnt26.mean():.1f} "
              f"cellstd={np.std(cell26):.3f} 噪底={noise:.3f} 结构显著={sig26:.2f}σ 字形峰谷(p98-p2)={apex:.2f} "
              f"格内笔画(≥1.0)={ink*100:.1f}%")
        # 13×13 半阶对照
        v13, q1, q2 = best_phase(res, m0, (b1v[0] / 2, b1v[1] / 2), (b2v[0] / 2, b2v[1] / 2), 13, 13, 20)
        cell13, cnt13 = fold_cell(res, m0, (b1v[0] / 2, b1v[1] / 2), (b2v[0] / 2, b2v[1] / 2), (q1, q2), 13, 13)
        noise13 = obs.std() / np.sqrt(max(1.0, cnt13.mean()))
        sig13 = float(np.std(cell13)) / max(1e-9, noise13)
        print(f"  [13×13 半阶] 相位=({q1:.2f},{q2:.2f}) cellstd={np.std(cell13):.3f} 结构显著={sig13:.2f}σ")
        if shared is None and name == "1.png":
            shared = (b1v, b2v)
    print("（注：'观测区=alpha==0'；幅度单位为灰度级；参考 docs/水印研究.md 口径）")


if __name__ == "__main__":
    main()
