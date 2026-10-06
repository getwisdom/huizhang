"""排版内核：模板槽位识别 + 自然序填充 + 页面合成 + 日志（对照 golden 阶段 2）。

参数语义对照旧实现（`legacy/排版工具.cs` / `legacy/layout.ps1`，提炼见
`docs/基线知识.md` §2）：

- 连通域识别：step=4 降采样、前景阈值 60、最小 300 采样点、合并 IoU 0.3、
  外扩 6px、中心十字弦拟合（r>10 失败）、半径下限 300；
- 槽位排序：**包围盒顶边 y 升序、再左边 x 升序**（用包围盒坐标，不是圆心坐标）；
- 底图：`StrCmpLogicalW` 自然序；alpha>16 包围盒；全透明跳过；扩展名白名单；
- 合成：画布=模板尺寸、白底、双三次（GDI+ 对齐参数见 `_COMPOSITE_*` 常量，W2 校准）；
- 槽位目标尺寸按模板圆盘实测重测（layout-fit：防检测半径被花色干扰导致出圈）；
- 定位点（layout-fit）：本工具自绘统一小三角（默认开启、可关；不依赖模板内容）；
- 页命名 `第N页.png`；写入前清空输出目录旧 `*.png`。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..logging_zh import write_log_file
from . import imaging
from .naming import natural_cmp

from functools import cmp_to_key

# —— 槽位识别参数（不可随意改动：与冻结基线对齐） ——
STEP = 4
FG_THRESHOLD = 60
MIN_REGION_PIXELS = 300
MERGE_IOU = 0.3
PAD = 6
MIN_FIT_RADIUS = 10
MIN_SLOT_RADIUS = 300.0

# —— 底图参数 ——
ALPHA_BBOX_THRESHOLD = 16
BASE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

# —— 合成参数（W2 校准结论：与 GDI+ DrawImage 的像素对齐，见 docs/汇报/07） ——
COMPOSITE_CONVENTION = "edge"   # "edge" | "center"
COMPOSITE_A = None              # None=实测 GDI+ 等效核；数字=Keys(a)（仅供校准对比）
COMPOSITE_PREMULT = False       # 是否按预乘 alpha 采样（实测两者几乎等价）
COMPOSITE_ROUND = "half_up"     # "half_up" | "half_even"（实测两者几乎等价）
# GDI+ 等效核参数（对 .NET HighQualityBicubic 灰底脉冲响应实测拟合）：
#   K(t) = mitchell(B=0.25, C=0.875) ⊛ box(0.75)（逐相 Σ=1.0000，残差 ≤2 灰阶）
GDI_B = 0.25
GDI_C = 0.875
GDI_BOX = 0.75

# —— 圆径实测与自绘定位点参数（layout-fit；对照模板实测，见该变更 design.md） ——
FIT_BAND = 70           # 圆径实测：中心行带（±px）
FIT_HALF = 470          # 圆径实测：单侧扫描窗口
FIT_THR = 215           # 圆径实测：内容判据 min(R,G,B) < 该值
FIT_MAX_DRIFT = 80      # 实测半径与检测半径偏差超此值视为异常 → 回退检测值
# —— 圆盘圆心实测参数（layout-center；现场实测：检测圆心被图案抬高 0.1~15.9px） ——
DISC_WHITE = 246        # 圆心实测：白底判据 min(R,G,B) >= 该值视为圆盘外的白底
DISC_RUN = 3            # 圆心实测：边界判据「连续 N 个非白像素」
DISC_ANGLES = 720       # 圆心实测：采样角数
DISC_TRIM = 3.0         # 圆心实测：截尾圆拟合内点容差（px）
DISC_ROUNDS = 3         # 圆心实测：截尾圆拟合轮数
DISC_OUT_SPAN = 60      # 圆心实测：外起点 = 检测半径 + 该值
DISC_IN_SPAN = 170      # 圆心实测：内终点 = 检测半径 - 该值
DISC_SCAN_MAX = 470.0   # 圆心实测：向外扫描上限（px）
DISC_SCAN_MIN = 150.0   # 圆心实测：向内扫描下限（px）
DISC_MAX_SHIFT = 40.0   # 圆心实测：圆心修正上限，超此值回退检测圆心
DISC_MIN_SHIFT = 1.0    # 圆心实测：修正量小于此值视为亚像素噪声 → 沿用检测圆心（保持既有模板逐像素不变）
DISC_MIN_RATIO = 0.5    # 圆心实测：拟合半径小于检测半径的该比例视为测错 → 回退（边界点取「首个非白」，比真实外缘小约 0.5px，故不用绝对阈值）
ANCHOR_EDGE_GAP = 8.5   # 定位点顶端距圆外缘
ANCHOR_HEIGHT = 17.0    # 轴向高
ANCHOR_HALF_BASE = 12.0 # 底半宽（底宽 24）
ANCHOR_STROKE = 6.5     # 描边宽（含约 1px 抗锯齿过渡）
ANCHOR_COLOR = (11, 9, 10)  # 近黑（沿用原设计色）


class LayoutError(Exception):
    """模板 / 底图不可用等业务错误（整体失败，日志记「错误: …」）。"""


@dataclass
class Slot:
    cx: float
    cy: float
    r: float


@dataclass
class BaseInfo:
    path: Path
    name: str
    min_x: int
    min_y: int
    max_x: int
    max_y: int
    image: np.ndarray  # RGBA uint8


@dataclass
class LayoutSummary:
    pages: int = 0
    slots: int = 0
    bases: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# 槽位识别
# ---------------------------------------------------------------------------

def _connected_components(mask: np.ndarray):
    """4 邻域连通域（返回已按 step 放大的包围盒与采样点数，序号即发现顺序）。"""
    from collections import deque

    sh, sw = mask.shape
    label = np.full((sh, sw), -1, dtype=np.int64)
    comps = []
    for start in range(sh * sw):
        sy, sx = divmod(start, sw)
        if not mask[sy, sx] or label[sy, sx] >= 0:
            continue
        idx = len(comps)
        x0 = y0 = 1 << 30
        x1 = y1 = -1
        cnt = 0
        q = deque([start])
        label[sy, sx] = idx
        while q:
            cur = q.popleft()
            cy, cx = divmod(cur, sw)
            if cx < x0:
                x0 = cx
            if cx > x1:
                x1 = cx
            if cy < y0:
                y0 = cy
            if cy > y1:
                y1 = cy
            cnt += 1
            if cx + 1 < sw and mask[cy, cx + 1] and label[cy, cx + 1] < 0:
                label[cy, cx + 1] = idx
                q.append(cy * sw + cx + 1)
            if cy + 1 < sh and mask[cy + 1, cx] and label[cy + 1, cx] < 0:
                label[cy + 1, cx] = idx
                q.append((cy + 1) * sw + cx)
            if cx - 1 >= 0 and mask[cy, cx - 1] and label[cy, cx - 1] < 0:
                label[cy, cx - 1] = idx
                q.append(cy * sw + cx - 1)
            if cy - 1 >= 0 and mask[cy - 1, cx] and label[cy - 1, cx] < 0:
                label[cy - 1, cx] = idx
                q.append((cy - 1) * sw + cx)
        comps.append(
            (x0 * STEP, y0 * STEP, (x1 + 1) * STEP - 1, (y1 + 1) * STEP - 1, cnt)
        )
    return comps


def _fit_circle_cross(rgb: np.ndarray, x0: int, y0: int, x1: int, y1: int):
    """包围盒中心十字弦拟合：圆心=弦中点，半径=max(水平弦长, 垂直弦长)/2。"""
    h, w = rgb.shape[0], rgb.shape[1]
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(w - 1, x1)
    y1 = min(h - 1, y1)
    cx0 = (x0 + x1) / 2.0
    cy0 = (y0 + y1) / 2.0
    yc = int(round(cy0))
    row = rgb[yc, x0 : x1 + 1, :3].astype(np.int32)
    hit = (
        np.abs(row[:, 0] - 255) + np.abs(row[:, 1] - 255) + np.abs(row[:, 2] - 255)
    ) > FG_THRESHOLD
    idx = np.flatnonzero(hit)
    if idx.size == 0:
        return None
    h_first = x0 + int(idx[0])
    h_last = x0 + int(idx[-1])
    xc = int(round(cx0))
    col = rgb[y0 : y1 + 1, xc, :3].astype(np.int32)
    hit = (
        np.abs(col[:, 0] - 255) + np.abs(col[:, 1] - 255) + np.abs(col[:, 2] - 255)
    ) > FG_THRESHOLD
    idy = np.flatnonzero(hit)
    if idy.size == 0:
        return None
    v_first = y0 + int(idy[0])
    v_last = y0 + int(idy[-1])
    wh = h_last - h_first + 1
    wv = v_last - v_first + 1
    cx = (h_first + h_last) / 2.0
    cy = (v_first + v_last) / 2.0
    r = max(wh, wv) / 2.0
    if r <= MIN_FIT_RADIUS:
        return None
    return cx, cy, r


def detect_slots(template_rgb: np.ndarray) -> list[Slot]:
    dh, dw = template_rgb.shape[0], template_rgb.shape[1]
    sw, sh = dw // STEP, dh // STEP
    sample = template_rgb[0 : sh * STEP : STEP, 0 : sw * STEP : STEP, :3].astype(np.int32)
    diff = (
        np.abs(sample[..., 0] - 255)
        + np.abs(sample[..., 1] - 255)
        + np.abs(sample[..., 2] - 255)
    )
    mask = diff > FG_THRESHOLD
    comps = _connected_components(mask)

    # 合并重叠包围盒（同一圆被切成多块的情况）——与旧实现同式
    merged = []
    used = [False] * len(comps)
    for i in range(len(comps)):
        ci = comps[i]
        if used[i] or ci[4] < MIN_REGION_PIXELS:
            continue
        bx0, by0, bx1, by1 = ci[0], ci[1], ci[2], ci[3]
        for j in range(i + 1, len(comps)):
            cj = comps[j]
            if used[j] or cj[4] < MIN_REGION_PIXELS:
                continue
            ox0 = max(bx0, cj[0])
            oy0 = max(by0, cj[1])
            ox1 = min(bx1, cj[2])
            oy1 = min(by1, cj[3])
            if ox1 <= ox0 or oy1 <= oy0:
                continue
            inter = (ox1 - ox0) * (oy1 - oy0)
            area = (bx1 - bx0) * (by1 - by0) + (cj[2] - cj[0]) * (cj[3] - cj[1]) - inter
            if inter / area > MERGE_IOU:
                used[j] = True
                bx0 = min(bx0, cj[0])
                by0 = min(by0, cj[1])
                bx1 = max(bx1, cj[2])
                by1 = max(by1, cj[3])
        used[i] = True
        merged.append((bx0, by0, bx1, by1))

    # 包围盒顶边 y 升序、再左边 x 升序（不是圆心坐标！）
    merged.sort(key=lambda b: (b[1], b[0]))

    slots: list[Slot] = []
    for bx0, by0, bx1, by1 in merged:
        fit = _fit_circle_cross(template_rgb, bx0 - PAD, by0 - PAD, bx1 + PAD, by1 + PAD)
        if fit is None:
            continue
        cx, cy, r = fit
        if r < MIN_SLOT_RADIUS:
            continue
        slots.append(Slot(cx=cx, cy=cy, r=r))
    return slots


# ---------------------------------------------------------------------------
# 底图
# ---------------------------------------------------------------------------

def load_base_infos(base_dir: Path):
    """按自然序读取底图，返回 (有效列表, 跳过名单)。"""
    if not base_dir.is_dir():
        raise LayoutError(f"找不到输入文件夹 {base_dir}")
    files = [p for p in base_dir.iterdir() if p.is_file()]
    files.sort(key=cmp_to_key(lambda a, b: natural_cmp(str(a), str(b))))
    infos: list[BaseInfo] = []
    skipped: list[str] = []
    for p in files:
        if p.suffix.lower() not in BASE_EXTS:
            continue
        rgba = imaging.load_rgba(p)
        mask = rgba[..., 3] > ALPHA_BBOX_THRESHOLD
        if not mask.any():
            skipped.append(p.name)
            continue
        ys, xs = np.nonzero(mask)
        infos.append(
            BaseInfo(
                path=p,
                name=p.name,
                min_x=int(xs.min()),
                min_y=int(ys.min()),
                max_x=int(xs.max()),
                max_y=int(ys.max()),
                image=rgba,
            )
        )
    return infos, skipped


# ---------------------------------------------------------------------------
# 合成（含可校准参数；W2 校准后常量固化）
# ---------------------------------------------------------------------------

_GDI_KERNEL_CACHE = None


def _gdi_kernel_table():
    """预计算 GDI+ 等效核（mitchell(B,C) ⊛ box）查找表（模块内一次）。"""
    global _GDI_KERNEL_CACHE
    if _GDI_KERNEL_CACHE is None:
        dt = 0.0005
        u = np.arange(-2.6, 2.6 + dt, dt)
        tv = np.abs(u)
        m = np.zeros_like(tv)
        m1 = tv < 1.0
        m2 = (tv >= 1.0) & (tv < 2.0)
        B, C = GDI_B, GDI_C
        m[m1] = (
            (12 - 9 * B - 6 * C) * tv[m1] ** 3
            + (-18 + 12 * B + 6 * C) * tv[m1] ** 2
            + (6 - 2 * B)
        ) / 6
        m[m2] = (
            (-B - 6 * C) * tv[m2] ** 3
            + (6 * B + 30 * C) * tv[m2] ** 2
            + (-12 * B - 48 * C) * tv[m2]
            + (8 * B + 24 * C)
        ) / 6
        box = np.where(np.abs(u) <= GDI_BOX / 2.0, 1.0 / GDI_BOX, 0.0)
        conv = np.convolve(m, box, mode="same") * dt
        _GDI_KERNEL_CACHE = (u, conv)
    return _GDI_KERNEL_CACHE


def _cubic_kernel(t: np.ndarray, a) -> np.ndarray:
    """插值核。

    a=None：W2 校准的「GDI+ 等效核」（灰底脉冲响应实测拟合：
    mitchell(0.25,0.875)⊛box(0.75)，逐相 Σ=1，残差 ≤2 灰阶）；
    传入数字：Keys 族 (a)，仅供校准脚本对比。
    """
    t = np.abs(np.asarray(t, dtype=np.float64))
    if a is None:
        gt, gv = _gdi_kernel_table()
        return np.interp(t, gt, gv, left=0.0, right=0.0)
    return np.where(
        t <= 1.0,
        (a + 2) * t**3 - (a + 3) * t**2 + 1.0,
        np.where(t < 2.0, a * t**3 - 5 * a * t**2 + 8 * a * t - 4 * a, 0.0),
    )


def _cubic_weights(xs: np.ndarray, a: float):
    base = np.floor(xs).astype(np.int64)
    offs = xs - base
    idxs = []
    weights = []
    for k in (-2, -1, 0, 1, 2, 3):
        idxs.append(base + k)
        weights.append(_cubic_kernel(offs - k, a))
    return idxs, weights


def _sample_2d(img: np.ndarray, sx: np.ndarray, sy: np.ndarray, a: float) -> np.ndarray:
    """在浮点坐标 (sx, sy) 网格上做双三次采样（边界按索引夹取，近似 edge 模式）。"""
    h, w = img.shape[0], img.shape[1]
    xi, wx = _cubic_weights(sx, a)
    yi, wy = _cubic_weights(sy, a)
    tmp = np.zeros((len(sy), w, img.shape[2]), dtype=np.float64)
    for k in range(len(yi)):
        idx = np.clip(yi[k], 0, h - 1)
        tmp += wy[k][:, None, None] * img[idx, :, :]
    out = np.zeros((len(sy), len(sx), img.shape[2]), dtype=np.float64)
    for k in range(len(xi)):
        idx = np.clip(xi[k], 0, w - 1)
        out += tmp[:, idx, :] * wx[k][None, :, None]
    return out


def _render_slot_patch(
    slot: Slot,
    info: BaseInfo,
    *,
    radius: float | None = None,
    center: tuple[float, float] | None = None,
    convention: str = COMPOSITE_CONVENTION,
    a: float = COMPOSITE_A,
    premult: bool = COMPOSITE_PREMULT,
    rounding: str = COMPOSITE_ROUND,
):
    """渲染一个槽位的合成补丁（白底上的最终 RGB），返回 (patch_uint8, (x0, y0))。

    radius：绘制目标半径（默认检测半径；layout-fit 传入按模板圆盘实测的重测值）。
    center：绘制中心（默认检测圆心；layout-center 传入圆盘实测校正后的圆心）。
    补丁原点为页面坐标，可能超出页面边界（由调用方裁剪）。
    """
    r = slot.r if radius is None else radius
    cx, cy = (slot.cx, slot.cy) if center is None else center
    dest_x = cx - r - 1.0
    dest_y = cy - r - 1.0
    dest_w = 2.0 * r + 2.0
    dest_h = dest_w
    src_x = float(info.min_x - 1)
    src_y = float(info.min_y - 1)
    src_w = float(info.max_x - info.min_x + 3)
    src_h = float(info.max_y - info.min_y + 3)

    rx0 = int(math.floor(dest_x)) - 2
    ry0 = int(math.floor(dest_y)) - 2
    rx1 = int(math.ceil(dest_x + dest_w)) + 2
    ry1 = int(math.ceil(dest_y + dest_h)) + 2

    xs = np.arange(rx0, rx1, dtype=np.float64) + 0.5
    ys = np.arange(ry0, ry1, dtype=np.float64) + 0.5
    sx = src_x + (xs - dest_x) * (src_w / dest_w)
    sy = src_y + (ys - dest_y) * (src_h / dest_h)
    if convention == "edge":
        sx = sx - 0.5
        sy = sy - 0.5

    img = info.image.astype(np.float64)
    if premult:
        img = img.copy()
        img[..., :3] *= img[..., 3:4] / 255.0

    sampled = _sample_2d(img, sx, sy, a)
    alpha = np.clip(sampled[..., 3], 0.0, 255.0)
    if premult:
        out = sampled[..., :3] + (255.0 - alpha)[..., None]
    else:
        out = sampled[..., :3] * (alpha / 255.0)[..., None] + (255.0 - alpha)[..., None]
    out = np.clip(out, 0.0, 255.0)
    if rounding == "half_up":
        out = np.floor(out + 0.5)
    else:
        out = np.rint(out)
    # 返回：（白底合成结果、采样 alpha（0..255 float，画布 SourceOver 用）、原点）
    return out.astype(np.uint8), alpha, (rx0, ry0)


# ---------------------------------------------------------------------------
# 圆径实测与定位点自绘（layout-fit）：徽章对齐模板圆盘 + 统一小三角
# ---------------------------------------------------------------------------

def _fit_slot_radius(template_rgb: np.ndarray, slot: Slot) -> float:
    """以检测槽位为种子，用「过中心行最大宽度」重测圆盘半径（对齐模板实物圆径）。

    检测半径在有花色图案的模板上可能被干扰偏大（实测 424 vs 实物 412），
    导致徽章「出圈」；此处按可见圆盘重测。测量失败或偏差异常时回退检测值。
    """
    h, w = template_rgb.shape[0], template_rgb.shape[1]
    cxi = math.floor(slot.cx + 0.5)
    cyi = math.floor(slot.cy + 0.5)
    best = None
    for y in range(max(0, cyi - FIT_BAND), min(h, cyi + FIT_BAND + 1)):
        x0 = max(0, cxi - FIT_HALF)
        x1 = min(w, cxi + FIT_HALF + 1)
        vals = template_rgb[y, x0:x1, :3].min(axis=1)
        idx = np.flatnonzero(vals < FIT_THR)
        if idx.size < 2:
            continue
        width = int(idx[-1]) - int(idx[0]) + 1
        if best is None or width > best:
            best = width
    if best is None:
        return slot.r
    r_fit = best / 2.0
    if r_fit < MIN_SLOT_RADIUS or abs(r_fit - slot.r) > FIT_MAX_DRIFT:
        return slot.r
    return r_fit


def _measure_slot_center(template_rgb: np.ndarray, slot: Slot) -> tuple[float, float]:
    """实测圆盘圆心（修正图案干扰造成的检测圆心偏移）；失败时回退检测圆心。

    圆盘之外是白底：自圆盘外向内取「首个连续 DISC_RUN 个非白像素」作边界点，
    以边界点质心为初值做截尾圆拟合（Kasa）。阈值与回退规则见本变更 design.md：
    修正量 < DISC_MIN_SHIFT（亚像素噪声）、拟合半径不足检测半径的 DISC_MIN_RATIO、或修正量越界（> DISC_MAX_SHIFT）时沿用检测圆心。
    """
    h, w = template_rgb.shape[0], template_rgb.shape[1]
    r_far = int(min(slot.r + DISC_OUT_SPAN, DISC_SCAN_MAX))
    r_near = int(max(slot.r - DISC_IN_SPAN, DISC_SCAN_MIN))
    if r_far <= r_near:
        return slot.cx, slot.cy
    ang = np.arange(DISC_ANGLES) * (2.0 * math.pi / DISC_ANGLES)
    cos_a, sin_a = np.cos(ang), np.sin(ang)
    rs = np.arange(r_far, r_near - 1, -1, dtype=np.float64)
    xs = np.clip(np.rint(slot.cx + np.outer(rs, cos_a)).astype(np.int64), 0, w - 1)
    ys = np.clip(np.rint(slot.cy + np.outer(rs, sin_a)).astype(np.int64), 0, h - 1)
    nonwhite = template_rgb[ys, xs, :3].min(axis=2) < DISC_WHITE
    runs = np.lib.stride_tricks.sliding_window_view(nonwhite, DISC_RUN, axis=0).all(axis=-1)
    found = runs.any(axis=0)
    if int(found.sum()) < DISC_ANGLES // 4:
        return slot.cx, slot.cy
    idx = runs.argmax(axis=0)[found]
    px = slot.cx + rs[idx] * cos_a[found]
    py = slot.cy + rs[idx] * sin_a[found]
    cx = float(px.mean())
    cy = float(py.mean())
    r_fit = float(np.median(np.hypot(px - cx, py - cy)))
    for _ in range(DISC_ROUNDS):
        keep = np.abs(np.hypot(px - cx, py - cy) - r_fit) < DISC_TRIM
        if int(keep.sum()) < 12:
            break
        kx, ky = px[keep], py[keep]
        mat = np.vstack([kx, ky, np.ones_like(kx)]).T
        sol, *_ = np.linalg.lstsq(mat, kx * kx + ky * ky, rcond=None)
        cx, cy = sol[0] / 2.0, sol[1] / 2.0
        r_fit = math.sqrt(max(sol[2] + cx * cx + cy * cy, 0.0))
    if r_fit < slot.r * DISC_MIN_RATIO or abs(r_fit - slot.r) > FIT_MAX_DRIFT:
        return slot.cx, slot.cy
    if math.hypot(cx - slot.cx, cy - slot.cy) > DISC_MAX_SHIFT:
        return slot.cx, slot.cy
    if math.hypot(cx - slot.cx, cy - slot.cy) < DISC_MIN_SHIFT:
        return slot.cx, slot.cy
    return float(cx), float(cy)


def _draw_anchor(canvas: np.ndarray, cx: float, cy: float, r: float) -> None:
    """绘制本工具统一的「定位点」：黑色空心小三角（尖朝上、紧贴圆内缘）。

    几何按实测圆径 r 固定（顶端距圆外缘 ANCHOR_EDGE_GAP；高/底宽/描边见常量）；
    以点到三边线段的距离场做 1px 抗锯齿绘制，仅改 RGB（中心空心透出底层）。
    """
    apex_x, apex_y = cx, cy - (r - ANCHOR_EDGE_GAP)
    left_x, left_y = cx - ANCHOR_HALF_BASE, apex_y + ANCHOR_HEIGHT
    right_x, right_y = cx + ANCHOR_HALF_BASE, apex_y + ANCHOR_HEIGHT
    pad = ANCHOR_STROKE / 2.0 + 2.0
    x0 = int(np.floor(cx - ANCHOR_HALF_BASE - pad))
    x1 = int(np.ceil(cx + ANCHOR_HALF_BASE + pad))
    y0 = int(np.floor(apex_y - pad))
    y1 = int(np.ceil(apex_y + ANCHOR_HEIGHT + pad))
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(canvas.shape[1] - 1, x1), min(canvas.shape[0] - 1, y1)
    if x1c <= x0c or y1c <= y0c:
        return
    gx = np.arange(x0c, x1c + 1, dtype=np.float64) + 0.5
    gy = np.arange(y0c, y1c + 1, dtype=np.float64) + 0.5
    px, py = np.meshgrid(gx, gy)

    def _edge_dist(ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
        return np.hypot(px - (ax + t * dx), py - (ay + t * dy))

    dist = np.minimum(
        np.minimum(
            _edge_dist(apex_x, apex_y, left_x, left_y),
            _edge_dist(apex_x, apex_y, right_x, right_y),
        ),
        _edge_dist(left_x, left_y, right_x, right_y),
    )
    cover = np.clip(ANCHOR_STROKE / 2.0 + 0.5 - dist, 0.0, 1.0)
    if not (cover > 0).any():
        return
    sub = canvas[y0c:y1c + 1, x0c:x1c + 1, :3].astype(np.float64)
    col = np.asarray(ANCHOR_COLOR, dtype=np.float64)
    blended = col[None, None, :] * cover[..., None] + sub * (1.0 - cover[..., None])
    canvas[y0c:y1c + 1, x0c:x1c + 1, :3] = np.clip(
        np.floor(blended + 0.5), 0.0, 255.0
    ).astype(np.uint8)


# ---------------------------------------------------------------------------
# 整批运行
# ---------------------------------------------------------------------------

def run_layout_batch(
    demo_path,
    base_dir,
    out_dir,
    *,
    anchors: bool = True,
    log_path=None,
    emit=None,
    progress=None,
    cancel=None,
):
    """排版批处理。返回 (LayoutSummary, 日志文本)；日志可选落盘（UTF-8 BOM）。"""
    demo_path = Path(demo_path)
    base_dir = Path(base_dir)
    out_dir = Path(out_dir)
    lines: list[str] = []

    def add(s: str) -> None:
        lines.append(s)
        if emit is not None:
            emit(s)

    summary = LayoutSummary()
    try:
        add("======== 徽章排版工具 ========")
        add(
            f"模板: {demo_path.name}   输入: {base_dir.name}\\*.png   "
            f"输出: {out_dir.name}\\第N页.png"
        )
        add("")
        if not demo_path.is_file():
            raise LayoutError(f"找不到模板文件 {demo_path.name}")
        template = imaging.load_rgb(demo_path)
        add(f"模板: {template.shape[1]}x{template.shape[0]}")
        slots = detect_slots(template)
        add(f"识别到 {len(slots)} 个槽位")
        if not slots:
            raise LayoutError("模板上没有识别到圆形槽位,请检查 排版demo.png")
        centers = [_measure_slot_center(template, s) for s in slots]
        radii = [_fit_slot_radius(template, s) for s in slots]
        add(
            f"圆盘实测: {len(slots)} 个槽位 圆径 {min(radii):.1f}~{max(radii):.1f} "
            f"圆心修正 ≤{max(math.hypot(c - s.cx, d - s.cy) for (c, d), s in zip(centers, slots)):.1f}px"
        )
        anchor_per_page = len(slots) if anchors else 0

        infos, skipped = load_base_infos(base_dir)
        add(f"底图数量: {len(infos)}")
        for name in skipped:
            add(f"跳过 {name}：没有有效内容")
        if not infos:
            raise LayoutError("底图文件夹里没有可用图片")
        for info in infos:
            cx = (info.min_x + info.max_x) / 2.0
            cy = (info.min_y + info.max_y) / 2.0
            r = max(info.max_x - info.min_x + 1, info.max_y - info.min_y + 1) / 2.0
            add(f"底图 {info.name}: 圆心=({cx:.1f},{cy:.1f}) 半径={r:.1f}")

        per_page = len(slots)
        total_pages = (len(infos) + per_page - 1) // per_page
        add(f"共 {total_pages} 页(每页 {per_page} 个槽位)")

        out_dir.mkdir(parents=True, exist_ok=True)
        for old in list(out_dir.glob("*.png")):
            try:
                old.unlink()
            except OSError:
                pass

        page_w = template.shape[1]
        page_h = template.shape[0]
        anchor_drawn = 0
        pages_drawn = 0
        for p in range(total_pages):
            if cancel is not None and cancel():
                break
            canvas = np.full((page_h, page_w, 4), 255, dtype=np.uint8)
            for i in range(per_page):
                idx = p * per_page + i
                if idx >= len(infos):
                    break
                info = infos[idx]
                slot = slots[i]
                patch, alpha, (px0, py0) = _render_slot_patch(
                    slot, info, radius=radii[i], center=centers[i]
                )
                ph, pw = patch.shape[0], patch.shape[1]
                cx0 = max(0, px0)
                cy0 = max(0, py0)
                cx1 = min(page_w, px0 + pw)
                cy1 = min(page_h, py0 + ph)
                if cx1 > cx0 and cy1 > cy0:
                    sub_patch = patch[cy0 - py0 : cy1 - py0, cx0 - px0 : cx1 - px0].astype(np.float64)
                    sub_alpha = alpha[cy0 - py0 : cy1 - py0, cx0 - px0 : cx1 - px0]
                    sub_canvas = canvas[cy0:cy1, cx0:cx1, :3].astype(np.float64)
                    # SourceOver：α 处保留画布已有内容（槽位目标框重叠时后画者叠加而非清空）
                    w = (255.0 - sub_alpha) / 255.0
                    blended = sub_patch + (sub_canvas - 255.0) * w[..., None]
                    canvas[cy0:cy1, cx0:cx1, :3] = np.clip(
                        np.floor(blended + 0.5), 0.0, 255.0
                    ).astype(np.uint8)
                add(
                    f"  p{p + 1} slot#{i + 1:>2} "
                    f"({math.floor(centers[i][0] + 0.5)},{math.floor(centers[i][1] + 0.5)})"
                    f" <- {info.name}"
                )
            if anchors:
                for i in range(per_page):
                    _draw_anchor(canvas, centers[i][0], centers[i][1], radii[i])
                    anchor_drawn += 1
            name = f"第{p + 1}页.png"
            imaging.save_rgba(out_dir / name, canvas)
            add(f"  已生成 {out_dir / name}")
            pages_drawn += 1
            if progress is not None:
                progress(p + 1, total_pages)
        if anchors:
            add(
                f"定位点: 已开启（共绘制 {anchor_drawn} 处："
                f"每页 {anchor_per_page} 处 × {pages_drawn} 页）"
            )
        else:
            add("定位点: 已关闭")
        add("")
        add("完成。请打开「已排版」文件夹查看结果。")
        summary = LayoutSummary(pages=total_pages, slots=per_page, bases=len(infos))
    except LayoutError as exc:
        add(f"错误: {exc}")
        summary.error = str(exc)

    text = "\n".join(lines) + "\n"
    if log_path is not None:
        write_log_file(log_path, text)
    return summary, text
