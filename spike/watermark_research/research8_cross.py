"""水印域测绘 v9（W3.1）：跨图折叠字形一致性（六图两两循环位移最大相关）。

复用 research7 的既有函数（不重复实现）：
- 角区定基（自相关亚像素峰）→ α=0 观测区 26×26 折叠（相位粗搜）；
- 对两两字形做 26×26 循环位移互相关，取最大相关系数（对齐各自相位系）。
另打印 4.png / 5.png 的逐像素最大差（重复图核查）。

输出为 UTF-8 文本；运行方式见 docs/水印研究.md。
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

from research7 import BASE, load_luma_alpha, med, corner_big, estimate_basis, fold_cell, best_phase

NAMES = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "测试_1.png"]


def max_cyclic_corr(a: np.ndarray, b: np.ndarray) -> float:
    A = a - a.mean()
    B = b - b.mean()
    na = np.sqrt(float(np.sum(A * A)))
    nb = np.sqrt(float(np.sum(B * B)))
    if na < 1e-9 or nb < 1e-9:
        return float("nan")
    best = -9.0
    n = a.shape[0]
    for dy in range(n):
        for dx in range(n):
            sh = np.roll(np.roll(B, dy, 0), dx, 1)
            r = float(np.sum(A * sh) / (na * np.sqrt(float(np.sum(sh * sh)))))
            if r > best:
                best = r
    return best


def main() -> None:
    names = sys.argv[1:] if len(sys.argv) > 1 else NAMES
    # 重复图核查
    if (BASE / "4.png").exists() and (BASE / "5.png").exists():
        a = np.asarray(Image.open(BASE / "4.png").convert("RGBA")).astype(np.int16)
        b = np.asarray(Image.open(BASE / "5.png").convert("RGBA")).astype(np.int16)
        d = int(np.abs(a - b).max()) if a.shape == b.shape else -1
        print(f"[重复图核查] 4.png vs 5.png 逐像素最大差 = {d}（0 表示内容完全一致）")
    glyphs = {}
    bases = {}
    for name in names:
        L, al = load_luma_alpha(BASE / name)
        res = L - med(L, 21)
        big, bmask = corner_big(res)
        basis, _ = estimate_basis(big, bmask)
        if len(basis) < 2:
            print(f"[{name}] 角区未能定基，跳过")
            continue
        b1v, b2v = basis
        m0 = al == 0
        v, p1, p2 = best_phase(res, m0, b1v, b2v, 26, 26, 20)
        cell, _ = fold_cell(res, m0, b1v, b2v, (p1, p2), 26, 26)
        glyphs[name] = cell
        bases[name] = (b1v, b2v, p1, p2)
        print(f"[{name}] 基=({b1v[0]:.3f},{b1v[1]:.3f})x({b2v[0]:.3f},{b2v[1]:.3f}) 相位=({p1:.2f},{p2:.2f}) cellstd={np.std(cell):.3f}")
    ns = list(glyphs)
    print("跨图字形最大相关（26×26 循环位移；+1 为完全一致）:")
    for i, ni in enumerate(ns):
        row = []
        for j, nj in enumerate(ns):
            if j < i:
                row.append("  .. ")
                continue
            r = max_cyclic_corr(glyphs[ni], glyphs[nj])
            row.append(f"{r:+.2f}")
        print("  " + f"{ni:>10s}", " ".join(row))


if __name__ == "__main__":
    main()
