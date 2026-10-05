"""抠图金标准对照（阶段 1 判据）：逐张核对尺寸、圆心/半径、像素级容差。"""

from pathlib import Path

import pytest

import helpers
from koutu.core import cutout

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "golden"
SRC_DIR = REPO / "原图"


def test_cutout_golden_batch(tmp_path):
    log_text = (GOLDEN / "logs" / "run_final" / "运行日志.txt").read_text(encoding="utf-8-sig")
    expected = helpers.parse_cutout_log(log_text)
    assert len(expected) == 7, "基线日志应含 7 条 [完成]"

    if not SRC_DIR.is_dir():
        pytest.skip("原图数据目录不存在")
    source_files = {p.name: p for p in SRC_DIR.glob("*.jpg")}
    missing = [n for n in expected if n not in source_files]
    if missing:
        pytest.skip(f"缺少源图: {missing}")

    results = {}
    for name in expected:
        out_path = tmp_path / (Path(name).stem + ".png")
        res = cutout.process_image(source_files[name], out_path, 45.0, 4, 4)
        assert res.ok, f"{name}: {res.error}"
        results[name] = res

    # 1) 尺寸与圆心/半径（容差 ±2px）
    for name, exp in expected.items():
        res = results[name]
        assert (res.width, res.height) == (exp["w"], exp["h"]), name
        assert abs(res.cx - exp["cx"]) <= 2 and abs(res.cy - exp["cy"]) <= 2, (
            name,
            res.cx,
            res.cy,
            exp,
        )
        assert abs(res.r - exp["r"]) <= 2, (name, res.r, exp["r"])

    # 2) 像素级（口径同 pixel-diff.ps1；阈值见 docs/验收清单.md 阶段 1）
    for name, exp in expected.items():
        base = helpers.load_rgba(GOLDEN / "baseline_products" / "底图" / exp["out"])
        mine = helpers.load_rgba(results[name].out_path)
        m = helpers.compare_rgba(base, mine)
        assert m["size_equal"], m
        rel = abs(m["opaque_a"] - m["opaque_b"]) / max(m["opaque_a"], 1)
        assert rel <= 0.005, (name, "不透明像素数偏差", m)
        assert m["alpha_gt8_ratio"] <= 0.005, (name, m)
        assert m["max_alpha_diff"] <= 64, (name, m)
        assert m["rgb_gt8_ratio"] <= 0.005, (name, m)
        print(
            f"[golden] {name}: opaque {m['opaque_a']}->{m['opaque_b']} "
            f"alpha>8 {m['alpha_gt8']} ({m['alpha_gt8_ratio']:.4%}) "
            f"maxAlpha {m['max_alpha_diff']} rgb>8 {m['rgb_gt8']} ({m['rgb_gt8_ratio']:.4%})"
        )
