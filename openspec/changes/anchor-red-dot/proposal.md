# 提案：anchor-red-dot —— 定位点样式可选（黑三角 / 红点）

## Why

- 使用者要求：**「提供选择可以使用红点方案」**。
- 事实（实测）：使用者现场模板的每个圆盘**正上方本来就有一枚纯红圆点**——11 个槽位中 7 个是紧凑圆点，实测 bbox ≈31~35px、圆心在槽位圆心正上方（角度 ≈ −90°、dx≈0）、中心半径 ≈ 圆盘外缘 + 9.6px、颜色 `(254, 0, 0)`（其余 4 个与相邻花纹粘连，取中位仍为纯红）。也就是该版式自带的付印对齐标记；当前工具只会自绘黑三角。
- 因此把「定位点样式」做成可选：默认仍是黑三角（不改变既有输出与基线），另提供「红点」——按现场模板红点实测的几何/颜色自绘统一红点。

## What Changes

- **内核** `koutu/core/layout.py`：
  - 新增常量 `ANCHOR_STYLE_TRIANGLE = "triangle"`、`ANCHOR_STYLE_DOT = "dot"`、`ANCHOR_DOT_DIAMETER = 32.0`、`ANCHOR_DOT_GAP = 9.5`、`ANCHOR_DOT_COLOR = (254, 0, 0)`；
  - 新增 `_draw_dot(canvas, cx, cy, r)`（实心圆、1px 抗锯齿）与 `_draw_marker(..., style)` 分派；`run_layout_batch(..., anchors=True, anchor_style="triangle")`；
  - 定位点仍与徽章**同源**（同一实测圆心与实测圆径）：红点圆心位于槽位圆心正上方、距圆盘外缘 `ANCHOR_DOT_GAP`。
- **日志**：定位点行改为 `定位点: 已开启（样式：黑三角|红点；共绘制 N 处：每页 N 处 × M 页）`；关闭时仍为 `定位点: 已关闭`。
- **CLI** `koutu layout --anchor-style {triangle,dot}`（中文 help；默认 `triangle`；非法值退出码 2）。`--anchors/--no-anchors` 语义不变。
- **GUI**「排版」页签：「添加定位点」右侧新增「样式」下拉（黑三角 / 红点），勾选框未勾选或任务运行中禁用；QSettings 记忆键 `layout/anchor_style`（与 `layout/anchors` 同一机制）。
- **测试**：新增 `tests/test_layout_marker_style.py`（红点几何/颜色/开-关差异仅限圆点区域/日志标注/GUI 记忆）；更新既有断言定位点日志文案的用例。
- **默认不变**：默认样式仍为黑三角 ⇒ 既有 golden 对照、现场输出与全部既有用例的像素结果不变。

### 非目标（Non-Goals）

- **不搬运模板像素**：仍然自绘统一标记（不把模板上的红点像素贴到输出页），与 `layout-fit` 的定向一致。
- 不新增第三种样式、不做样式自动识别（不从模板推断该用哪种）。
- 不改半径/圆心实测逻辑、不改开关默认值（默认开启 + 黑三角）、不改目录契约。

## Capabilities

### Modified Capabilities

- `badge-layout`：「定位点绘制（默认开启、可关闭）」（样式可选 + 日志标注样式）。
- `desktop-gui`：「排版定位点开关（勾选框与记忆）」（新增样式下拉与 `layout/anchor_style` 记忆）。
- `pipeline-orchestration`：「排版定位点 CLI 开关」（新增 `--anchor-style`）。

## Impact

- 变更产物：`openspec/changes/anchor-red-dot/`（proposal / specs / design / tasks）。
- 实现：`koutu/core/layout.py`、`koutu/cli/main.py`、`koutu/gui/pages.py`、`koutu/gui/worker.py`、`koutu/gui/main_window.py`。
- 测试：`tests/test_layout_marker_style.py`（新增）、`tests/test_layout_anchors.py`、`tests/test_cli_layout.py`、`tests/test_gui_smoke.py`。
- 文档/验收：`docs/验收清单.md`、`使用说明.txt`（界面/CLI/日志说明）、`docs/汇报/18-*.md`。
- 交付：`packaging\打包.ps1` 重建 `dist\koutu\`（重建前备份现场）并复跑对照。
- 保持：13 个数据目录、`golden/`、`legacy/`、已归档变更与 `flexible-io` 不动。
