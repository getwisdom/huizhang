"""排版金标准对照（阶段 2 判据）：整页像素 + 分配表逐行 + 页数/尺寸。"""

from pathlib import Path

import helpers
from koutu.core import layout

REPO = Path(__file__).resolve().parents[1]
GOLDEN = REPO / "golden"
DEMO = REPO / "排版demo.png"
BASE = GOLDEN / "baseline_products" / "底图"
PAGE = GOLDEN / "baseline_products" / "已排版" / "第1页.png"
GOLDEN_LOG = GOLDEN / "logs" / "run_final" / "_layout_log.txt"


def test_layout_golden_page(tmp_path):
    out = tmp_path / "已排版"
    summary, text = layout.run_layout_batch(DEMO, BASE, out)
    assert summary.error is None, summary.error
    assert (summary.pages, summary.slots, summary.bases) == (1, 11, 7)

    page = helpers.load_rgba(out / "第1页.png")
    golden = helpers.load_rgba(PAGE)
    assert page.shape == golden.shape == (3508, 2480, 4)

    m = helpers.compare_rgba(golden, page)
    print(
        "[golden-layout] "
        f"opaque {m['opaque_a']}->{m['opaque_b']} | "
        f"alpha>8 {m['alpha_gt8']} ({m['alpha_gt8_ratio']:.4%}) maxA {m['max_alpha_diff']} | "
        f"rgb>8 {m['rgb_gt8']} ({m['rgb_gt8_ratio']:.4%})"
    )
    assert m["alpha_gt8_ratio"] <= 0.005, m
    assert m["max_alpha_diff"] <= 64, m
    assert m["rgb_gt8_ratio"] <= 0.005, m

    # 页数与分配表逐行一致（坐标容差 ±2px）
    golden_text = GOLDEN_LOG.read_text(encoding="utf-8-sig")
    g_alloc = helpers.parse_layout_alloc(golden_text)
    m_alloc = helpers.parse_layout_alloc(text)
    assert len(g_alloc) == 7 and len(m_alloc) == 7
    for ours, exp in zip(m_alloc, g_alloc):
        assert (ours["page"], ours["slot"], ours["file"]) == (exp["page"], exp["slot"], exp["file"])
        assert abs(ours["x"] - exp["x"]) <= 2 and abs(ours["y"] - exp["y"]) <= 2
    assert "共 1 页(每页 11 个槽位)" in text
