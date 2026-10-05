"""水印域测绘 v2（W3.1）：中值残差 + 27px 相位搜索 + 折叠细胞模板。"""

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


def load_luma(path: Path):
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[..., :3].astype(np.float32)
    L = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return L, rgba[..., 3]


def med21(L: np.ndarray) -> np.ndarray:
    u8 = np.clip(np.rint(L), 0, 255).astype(np.uint8)
    m = Image.fromarray(u8, "L").filter(ImageFilter.MedianFilter(21))
    return np.asarray(m).astype(np.float32)


def site_score(res: np.ndarray, mask: np.ndarray, px: float, py: float, pitch: float) -> float:
    h, w = res.shape
    xs = np.arange(px, w - 1, pitch)
    ys = np.arange(py, h - 1, pitch)
    scores = []
    for y in ys:
        yi = int(round(y))
        for x in xs:
            xi = int(round(x))
            if xi - 3 < 0 or yi - 3 < 0 or xi + 4 > w or yi + 4 > h:
                continue
            if mask[yi - 3 : yi + 4, xi - 3 : xi + 4].mean() < 0.95:
                continue
            window = res[yi - 3 : yi + 4, xi - 3 : xi + 4]
            scores.append(np.percentile(window, 90))  # 站点邻域 90 分位（对笔画面）
    if len(scores) < 20:
        return float("nan"), 0
    return float(np.mean(scores)), len(scores)


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else [f"{i}.png" for i in range(1, 7)] + ["测试_1.png"]
    for name in names:
        L, alpha = load_luma(BASE / name)
        mask = alpha > 240
        res = L - med21(L)
        r_in = res[mask]
        print(f"\n===== {name} 有效 {mask.mean():.1%}  残差std={r_in.std():.2f}  p99={np.percentile(r_in, 99):.2f} =====")

        # 相位搜索（pitch=27）
        best = []
        for py in np.arange(0, 27, 1.0):
            for px in np.arange(0, 27, 1.0):
                s, n = site_score(res, mask, px, py, 27.0)
                best.append((s, px, py, n))
        best.sort(reverse=True, key=lambda b: (b[0] if not np.isnan(b[0]) else -9))
        top = best[:5]
        others = [b[0] for b in best[5:] if not np.isnan(b[0])]
        q90 = np.percentile(others, 90) if others else float("nan")
        print(f"  相位 top5（pitch=27）: " + " | ".join(f"({int(p)},{int(q)})→{s:.3f}" for s, p, q, _ in top))
        print(f"  其余相位 90 分位={q90:.3f}")
        s0, px0, py0, n0 = top[0]
        if np.isnan(s0):
            print("  无有效相位")
            continue

        # 折叠细胞模板（27×27，按最近整格分箱）
        cell_sum = np.zeros((27, 27), dtype=np.float64)
        cell_cnt = np.zeros((27, 27), dtype=np.float64)
        h, w = res.shape
        ys, xs = np.nonzero(mask)
        ux = np.mod(xs - px0 + 0.5, 27.0) - 0.5
        uy = np.mod(ys - py0 + 0.5, 27.0) - 0.5
        bx = np.clip(np.round(ux + 13.5).astype(int), 0, 26)
        by = np.clip(np.round(uy + 13.5).astype(int), 0, 26)
        np.add.at(cell_sum, (by, bx), res[ys, xs])
        np.add.at(cell_cnt, (by, bx), 1.0)
        cell = np.where(cell_cnt > 0, cell_sum / np.maximum(cell_cnt, 1), 0.0)

        cmin, cmax = np.percentile(cell[cell_cnt > 30], [2, 98]) if (cell_cnt > 30).any() else (0, 1)
        print(f"  细胞模板（27×27，2–98 分位 {cmin:.2f}..{cmax:.2f}，字符=亮）:")
        chars = " .:-=+*#%@"
        for r in range(27):
            row = ""
            for c in range(27):
                if cell_cnt[r, c] < 30:
                    row += "?"
                    continue
                v = (cell[r, c] - cmin) / max(1e-6, cmax - cmin)
                row += chars[int(np.clip(v, 0, 0.999) * len(chars))]
            print("   " + row)
        on_site = np.mean(cell[cell_cnt > 30])
        print(f"  折叠细胞均值={on_site:.3f}（站点样本 {n0}）")


if __name__ == "__main__":
    main()
