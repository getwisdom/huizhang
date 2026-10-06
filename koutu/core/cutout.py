"""抠图内核：四边扫描 + RANSAC + Kasa 精修 + 羽化裁切。

参数语义逐项对照旧实现（`legacy/抠图工具.cs` / `legacy/cut_badge.ps1`，
提炼见 `docs/基线知识.md` §1）：

- 40 条扫描线（20 水平 + 20 垂直），覆盖 14%–86%；起始端 5%–10% 边缘带取参考色；
- 9 像素邻域均值，判定 `|ΔR|+|ΔG|+|ΔB| > ScanT`（默认 45）；候选点 <6 失败；
- RANSAC：`Random(2024)`、600 次、3 点定圆、共线跳过；半径 [0.10,0.70]×min、
  圆心 15%–85%；内点容差 4px；最多内点 <8 失败；
- Kasa 精修：取 ≤6px 的点、容差 5px、至多 6 轮；接受条件 [0.08,0.75]×min 且圆心在图内；
- 羽化线性（默认 4px）、裁切边距 4px、外接正方形、32 位 ARGB 输出。

随机序列用 `dotnet_random.DotNetRandom` 逐位复刻 .NET 实现，保证与旧 exe
在同一输入上得到同一组采样（进而同一拟合结果）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import imaging
from .dotnet_random import DotNetRandom
from .pipeline import BatchSummary, execute_batch


@dataclass
class CutoutResult:
    name: str
    ok: bool
    error: str = ""
    out_name: str = ""
    out_path: str = ""
    width: int = 0
    height: int = 0
    cx: float = 0.0
    cy: float = 0.0
    r: float = 0.0
    scan_points: int = 0
    inliers: int = 0

    @property
    def stat_line(self) -> str:
        """对照旧日志：`OK 417x417 圆心(414,365) 半径200`（四舍五入与 .NET 一致）。"""
        return (
            f"OK {self.width}x{self.height} "
            f"圆心({int(round(self.cx))},{int(round(self.cy))}) 半径{int(round(self.r))}"
        )


# ---------------------------------------------------------------- 扫描

def _band_mean(img: np.ndarray, start: int, end: int, *, vertical: bool, fixed: int):
    seg = img[start:end, fixed, :3] if vertical else img[fixed, start:end, :3]
    n = int(seg.shape[0])
    if n == 0:
        return None
    m = seg.astype(np.int64).sum(axis=0) // n
    return int(m[0]), int(m[1]), int(m[2])


def _win_mean(img: np.ndarray, y: int, x: int, *, vertical: bool):
    h, w = int(img.shape[0]), int(img.shape[1])
    if vertical:
        seg = img[max(0, y - 4): min(h, y + 5), x, :3]
    else:
        seg = img[y, max(0, x - 4): min(w, x + 5), :3]
    n = int(seg.shape[0])
    if n == 0:
        return None
    m = seg.astype(np.int64).sum(axis=0) // n
    return int(m[0]), int(m[1]), int(m[2])


def _scan_points(img: np.ndarray, scan_t: float):
    """四边扫描取边界候选点（返回顺序与旧实现一致：水平线左→右，垂直线顶→底）。"""
    h, w = int(img.shape[0]), int(img.shape[1])
    pts: list[tuple[float, float]] = []

    # 水平 20 条
    for li in range(20):
        y = int(h * (0.14 + 0.72 * li / 19.0))
        ref_l = _band_mean(img, int(w * 0.05), int(w * 0.10), vertical=False, fixed=y)
        if ref_l is None:
            continue
        xl = -1
        for x in range(int(w * 0.14), w // 2 + 1):
            m = _win_mean(img, y, x, vertical=False)
            if m is None:
                continue
            if abs(m[0] - ref_l[0]) + abs(m[1] - ref_l[1]) + abs(m[2] - ref_l[2]) > scan_t:
                xl = x
                break
        ref_r = _band_mean(img, int(w * 0.90), int(w * 0.95), vertical=False, fixed=y)
        if ref_r is None:
            if xl >= 0:
                pts.append((float(xl), float(y)))
            continue
        xr = -1
        for x in range(int(w * 0.86), w // 2 - 1, -1):
            m = _win_mean(img, y, x, vertical=False)
            if m is None:
                continue
            if abs(m[0] - ref_r[0]) + abs(m[1] - ref_r[1]) + abs(m[2] - ref_r[2]) > scan_t:
                xr = x
                break
        if xl >= 0:
            pts.append((float(xl), float(y)))
        if xr >= 0:
            pts.append((float(xr), float(y)))

    # 垂直 20 条
    for li in range(20):
        x = int(w * (0.14 + 0.72 * li / 19.0))
        ref_t = _band_mean(img, int(h * 0.05), int(h * 0.10), vertical=True, fixed=x)
        if ref_t is None:
            continue
        yt = -1
        for y in range(int(h * 0.14), h // 2 + 1):
            m = _win_mean(img, y, x, vertical=True)
            if m is None:
                continue
            if abs(m[0] - ref_t[0]) + abs(m[1] - ref_t[1]) + abs(m[2] - ref_t[2]) > scan_t:
                yt = y
                break
        ref_b = _band_mean(img, int(h * 0.90), int(h * 0.95), vertical=True, fixed=x)
        if ref_b is None:
            if yt >= 0:
                pts.append((float(x), float(yt)))
            continue
        yb = -1
        for y in range(int(h * 0.86), h // 2 - 1, -1):
            m = _win_mean(img, y, x, vertical=True)
            if m is None:
                continue
            if abs(m[0] - ref_b[0]) + abs(m[1] - ref_b[1]) + abs(m[2] - ref_b[2]) > scan_t:
                yb = y
                break
        if yt >= 0:
            pts.append((float(x), float(yt)))
        if yb >= 0:
            pts.append((float(x), float(yb)))
    return pts


# ---------------------------------------------------------------- 拟合

def _circle_from_3(x1, y1, x2, y2, x3, y3):
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return None
    s1 = x1 * x1 + y1 * y1
    s2 = x2 * x2 + y2 * y2
    s3 = x3 * x3 + y3 * y3
    cx = (s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)) / d
    cy = (s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)) / d
    r = math.sqrt((x1 - cx) * (x1 - cx) + (y1 - cy) * (y1 - cy))
    return cx, cy, r


def _fit_circle(pts, tol: float, iters: int):
    """Kasa 最小二乘（内点重估），与旧实现逐式对应。"""
    n = len(pts)
    xa = [p[0] for p in pts]
    ya = [p[1] for p in pts]
    use = [True] * n
    cx = cy = r = 0.0
    for it in range(iters):
        Sx = Sy = Sxx = Syy = Sxy = Sxxx = Syyy = Sxyy = Sxxy = 0.0
        m = 0
        for i in range(n):
            if not use[i]:
                continue
            x, y = xa[i], ya[i]
            Sx += x
            Sy += y
            Sxx += x * x
            Syy += y * y
            Sxy += x * y
            Sxxx += x * x * x
            Syyy += y * y * y
            Sxyy += x * y * y
            Sxxy += x * x * y
            m += 1
        if m < 3:
            break
        A11 = 2 * Sxx - 2 * Sx * Sx / m
        A12 = 2 * Sxy - 2 * Sx * Sy / m
        A22 = 2 * Syy - 2 * Sy * Sy / m
        B1 = Sxxx + Sxyy - (Sxx + Syy) * Sx / m
        B2 = Syyy + Sxxy - (Sxx + Syy) * Sy / m
        det = A11 * A22 - A12 * A12
        if abs(det) < 1e-12:
            break
        u = (B1 * A22 - B2 * A12) / det
        v = (B2 * A11 - B1 * A12) / det
        cx = -u / 2
        cy = -v / 2
        sum_r = 0.0
        nr = 0
        for i in range(n):
            if not use[i]:
                continue
            sum_r += math.sqrt((xa[i] - cx) * (xa[i] - cx) + (ya[i] - cy) * (ya[i] - cy))
            nr += 1
        if nr > 0:
            r = sum_r / nr
        changed = False
        for i in range(n):
            dist = math.sqrt((xa[i] - cx) * (xa[i] - cx) + (ya[i] - cy) * (ya[i] - cy))
            nu = abs(dist - r) <= tol
            if nu != use[i]:
                use[i] = nu
                changed = True
        if not changed and it >= 1:
            break
    inliers = sum(1 for u_ in use if u_)
    return cx, cy, r, inliers


def _ransac(pts, w: int, h: int):
    n = len(pts)
    best_cx = best_cy = best_r = 0.0
    best_in = -1
    rnd = DotNetRandom(2024)
    min_dim = min(w, h)
    for _ in range(600):
        a = rnd.next(n)
        b = rnd.next(n)
        c = rnd.next(n)
        if a == b or b == c or a == c:
            continue
        circle = _circle_from_3(
            pts[a][0], pts[a][1], pts[b][0], pts[b][1], pts[c][0], pts[c][1]
        )
        if circle is None:
            continue
        cx, cy, r = circle
        if r < min_dim * 0.10 or r > min_dim * 0.70:
            continue
        if cx < w * 0.15 or cx > w * 0.85 or cy < h * 0.15 or cy > h * 0.85:
            continue
        inn = 0
        for px_, py_ in pts:
            dd = math.sqrt((px_ - cx) * (px_ - cx) + (py_ - cy) * (py_ - cy))
            if abs(dd - r) <= 4.0:
                inn += 1
        if inn > best_in:
            best_in = inn
            best_cx, best_cy, best_r = cx, cy, r
    return best_cx, best_cy, best_r, best_in


# ---------------------------------------------------------------- 单张处理

def process_image(src_path, dst_path, scan_t: float = 45.0, feather: int = 4, margin: int = 4) -> CutoutResult:
    name = Path(src_path).name
    try:
        img = imaging.load_rgb(src_path)
    except Exception as exc:
        return CutoutResult(name=name, ok=False, error=f"读取失败: {exc}")

    h, w = int(img.shape[0]), int(img.shape[1])
    pts = _scan_points(img, float(scan_t))
    if len(pts) < 6:
        return CutoutResult(
            name=name, ok=False, error=f"边界点不足({len(pts)})，未找到圆形徽章", scan_points=len(pts)
        )

    bx, by, br, best_in = _ransac(pts, w, h)
    if best_in < 8:
        return CutoutResult(
            name=name,
            ok=False,
            error=f"未找到可靠的圆形(最多内点 {best_in})",
            scan_points=len(pts),
            inliers=best_in,
        )

    # 最小二乘精修（只改善、不劣化）
    in_pts = [
        p for p in pts
        if abs(math.sqrt((p[0] - bx) * (p[0] - bx) + (p[1] - by) * (p[1] - by)) - br) <= 6.0
    ]
    fcx, fcy, fr, fin = _fit_circle(in_pts, 5.0, 6)
    if fin >= 8 and fr > 0:
        min_dim = min(w, h)
        if (
            fr >= min_dim * 0.08
            and fr <= min_dim * 0.75
            and fcx > 0
            and fcy > 0
            and fcx < w
            and fcy < h
        ):
            bx, by, br, best_in = fcx, fcy, fr, fin

    # 裁切范围与外接正方形
    cx0 = max(0, int(bx - br - feather - margin))
    cy0 = max(0, int(by - br - feather - margin))
    cx1 = min(w - 1, int(bx + br + feather + margin))
    cy1 = min(h - 1, int(by + br + feather + margin))
    cw = cx1 - cx0 + 1
    ch = cy1 - cy0 + 1

    # 圆内 alpha=255、圆外 0、边缘线性羽化（与旧实现同式）
    xs = np.arange(cw, dtype=np.float64) + (cx0 + 0.5)
    ys = np.arange(ch, dtype=np.float64) + (cy0 + 0.5)
    dx = xs - bx
    dy = ys - by
    dist = np.sqrt(dy[:, None] ** 2 + dx[None, :] ** 2)
    if feather > 0:
        v = (br + feather - dist) / feather * 255.0 + 0.5
        v = np.where(dist <= br, 255.0, v)
        v = np.where(dist >= br + feather, 0.0, v)
        alpha = np.maximum(0.0, np.minimum(255.0, v)).astype(np.uint8)
    else:
        alpha = np.where(dist <= br, 255.0, 0.0).astype(np.uint8)

    out = np.empty((ch, cw, 4), dtype=np.uint8)
    out[:, :, :3] = img[cy0: cy0 + ch, cx0: cx0 + cw, :3]
    out[:, :, 3] = alpha
    try:
        imaging.save_rgba(dst_path, out)
    except Exception as exc:
        return CutoutResult(name=name, ok=False, error=f"保存失败: {exc}", scan_points=len(pts))

    return CutoutResult(
        name=name,
        ok=True,
        out_name=Path(dst_path).name,
        out_path=str(dst_path),
        width=cw,
        height=ch,
        cx=bx,
        cy=by,
        r=br,
        scan_points=len(pts),
        inliers=best_in,
    )


# ---------------------------------------------------------------- 批处理

def list_images(directory: Path):
    """按扩展名收集图片；顺序与旧实现一致（文件名序数序、忽略大小写）。"""
    directory = Path(directory)
    found = {}
    for ext in ("jpg", "jpeg", "png", "bmp", "gif", "tif", "tiff"):
        for p in directory.glob(f"*.{ext}"):
            if p.is_file():
                found.setdefault(str(p).upper(), p)
    return sorted(found.values(), key=lambda p: p.name.upper())


def run_cutout_batch(
    src_dir,
    dst_dir,
    *,
    scan_t: float = 45.0,
    feather: int = 4,
    margin: int = 4,
    log_path=None,
    emit=None,
    on_progress=None,
    cancel=None,
):
    """批处理抠图：返回 (BatchSummary, 日志全文)。

    日志口径（flexible-io D6）：记完整输入/输出路径；成功/失败/取消都落盘并带
    中文状态行；任务开始前给出同名覆盖计数提示（不打断）。
    """
    from ..logging_zh import fmt_num, write_log_file

    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    lines: list[str] = []

    def add(text: str) -> None:
        lines.append(text)
        if emit is not None:
            emit(text)

    def write_now() -> None:
        if log_path is not None:
            write_log_file(log_path, "\n".join(lines) + "\n")

    try:
        src_dir.mkdir(parents=True, exist_ok=True)
        dst_dir.mkdir(parents=True, exist_ok=True)
        files = list_images(src_dir)

        add("徽章抠图工具")
        add(f"原图: {src_dir} ({len(files)} 张)")
        add(f"输出: {dst_dir}")
        add(f"参数: 扫描阈值={fmt_num(scan_t)}  羽化={feather}px  边距={margin}px")
        overwrite = sum(1 for f in files if (dst_dir / f"{f.stem}.png").is_file())
        add(f"运行前: 输入 {len(files)} 张；同名覆盖 {overwrite} 个；抠图不清理输出目录")
        add("------------------------------")

        if not files:
            add("[提示] 原图文件夹里没有图片文件")

        def process_one(src_file: Path) -> str:
            out_path = dst_dir / (src_file.stem + ".png")
            res = process_image(src_file, out_path, scan_t, feather, margin)
            if res.ok:
                add(f"[完成] {src_file.name} -> {res.out_name}  ({res.stat_line})")
                return f"[完成] {src_file.name}"
            add(f"[失败] {src_file.name}  {res.error}")
            return f"[失败] {src_file.name}"

        summary = execute_batch(
            files, process_one, emit=None, on_progress=on_progress, cancel=cancel
        )
        # execute_batch 负责计数；上面 process_one 已负责输出行（避免重复 emit）
        lines.append("------------------------------")
        if summary.cancelled:
            tail = f"已取消：成功 {summary.ok} 张，失败 {summary.fail} 张"
        else:
            tail = f"全部完成：成功 {summary.ok} 张，失败 {summary.fail} 张"
        lines.append(tail)
        if emit is not None:
            emit("------------------------------")
            emit(tail)
    except Exception as exc:  # 兜底：任何异常也落盘本次日志并带中文状态行（D6）
        if not any(line.startswith("原图:") for line in lines):
            add(f"原图: {src_dir}")
            add(f"输出: {dst_dir}")
        add(f"错误: 未预期错误（{type(exc).__name__}）")
        write_now()
        raise

    text = "\n".join(lines) + "\n"
    write_now()
    return summary, text
