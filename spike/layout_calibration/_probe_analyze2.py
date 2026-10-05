"""探针分析 v2（开发用）：三方对照 + 多尺度脉冲响应表。"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\workspace\koutu")
REPO = Path(__file__).resolve().parents[1]


def load_gray(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"))[..., 0].astype(np.float64)


def load_rgba(p: Path) -> np.ndarray:
    return np.asarray(Image.open(p).convert("RGBA"), dtype=np.uint8)


def main() -> None:
    # 1) 三方对照：真实槽位 GDI+ 探针 vs golden 页 vs 我们的补丁
    sys.path.insert(0, str(REPO))
    from koutu.core import imaging, layout

    page = load_rgba(REPO / "golden" / "baseline_products" / "已排版" / "第1页.png")
    probe = load_rgba(TEMP / "probe_slot1.png")
    template = imaging.load_rgb(REPO / "排版demo.png")
    slots = layout.detect_slots(template)
    infos, _ = layout.load_base_infos(REPO / "golden" / "baseline_products" / "底图")
    slot, info = slots[0], infos[0]
    patch, (px0, py0) = layout._render_slot_patch(slot, info, convention="edge", a=-0.5)
    ph, pw = patch.shape[0], patch.shape[1]

    g_page = page[py0 : py0 + ph, px0 : px0 + pw, :3]
    g_probe = probe[py0 : py0 + ph, px0 : px0 + pw, :3]

    d1 = np.abs(probe[py0 : py0 + ph, px0 : px0 + pw, :3].astype(np.int16) - g_page.astype(np.int16))
    d2 = np.abs(patch.astype(np.int16) - g_probe.astype(np.int16))
    for name, d in (("probe-vs-golden", d1), ("ours-vs-probe", d2)):
        gt8 = int((d.max(axis=2) > 8).sum())
        print(f"{name}: gt8={gt8} ({gt8 / d[..., 0].size:.4%})  mean={d.mean():.4f}  max={d.max()}")

    # 2) 脉冲响应表：scale=2 与 scale=10
    for tag, path, scale, center_col in (
        ("s2", TEMP / "impulse_s2.png", 2.0, 16),
        ("s10", TEMP / "impulse_s10.png", 10.0, 16),
    ):
        if not path.is_file():
            print(f"[{tag}] missing: {path}")
            continue
        img = load_gray(path)
        row = img.shape[0] // 2
        prof = img[row]
        # 脉冲中心：源列 center_col 的中心（边坐标 center_col+0.5）映射到目标边坐标
        cc = (center_col + 0.5) * scale
        print(f"\n[{tag}] scale={scale} destW={img.shape[1]} 中心边坐标={cc:.2f}")
        print("t(源像素单位) : 实测值/255")
        lo = int(cc - 2.2 * scale)
        hi = int(cc + 2.2 * scale) + 1
        for px in range(max(0, lo), min(img.shape[1], hi)):
            t = (px + 0.5) / scale - (center_col + 0.5)
            print(f"  t={t:+.4f}  v={prof[px] / 255.0:.4f}")


if __name__ == "__main__":
    main()
