# 任务：anchor-red-dot

## 1. 实现（内核）

- [x] 1.1 `koutu/core/layout.py`：新增常量 `ANCHOR_STYLE_TRIANGLE="triangle"`、`ANCHOR_STYLE_DOT="dot"`、`ANCHOR_DOT_DIAMETER=32.0`、`ANCHOR_DOT_GAP=9.5`、`ANCHOR_DOT_COLOR=(254,0,0)`
- [x] 1.2 新增 `_draw_dot(canvas, cx, cy, r)`（实心圆 + 1px 抗锯齿，与 `_draw_anchor` 同一写法）与 `_draw_marker(canvas, cx, cy, r, style)` 分派
- [x] 1.3 `run_layout_batch(..., anchor_style=ANCHOR_STYLE_TRIANGLE)`：按样式绘制定位点；日志行改为 `定位点: 已开启（样式：黑三角|红点；共绘制 N 处：每页 N 处 × M 页）`
- [x] 1.4 未知样式值：回退为黑三角并照常运行（或按 argparse 拦截；GUI 下拉不可输入非法值）

## 2. 实现（CLI 与 GUI）

- [x] 2.1 `koutu/cli/main.py`：`--anchor-style {triangle,dot}`（中文 help，默认 `triangle`）→ 传给 `run_layout_batch`
- [x] 2.2 `koutu/gui/pages.py`：`LayoutPage` 新增 `cmb_anchor_style`（「黑三角」/「红点」）；未勾选或运行中禁用（`set_busy`）；勾选框联动
- [x] 2.3 `koutu/gui/main_window.py`：启动读取 `layout/anchor_style`（默认 triangle）、任务传参、关闭时写回
- [x] 2.4 `koutu/gui/worker.py`：`make_layout_task(..., anchors=True, anchor_style="triangle")`

## 3. 测试

- [x] 3.1 新增 `tests/test_layout_marker_style.py`：红点几何（直径/横向居中/中心半径 = 圆径+9.5）/颜色 `(254,0,0)`/开-关差异仅限圆点区域/日志标注样式；非默认样式不影响徽章像素
- [x] 3.2 更新既有断言：`tests/test_layout_anchors.py`、`tests/test_cli_layout.py`（定位点日志行新增「样式：黑三角」）；`tests/test_gui_smoke.py` 增补样式下拉默认值/禁用/记忆
- [x] 3.3 `.venv\Scripts\python.exe -m pytest tests -q` 全绿；`test_layout_golden.py` 数字照旧

## 4. 实跑与像素证据

- [x] 4.1 独立运行目录：现场模板分别以黑三角 / 红点 / 关闭跑一遍，贴日志行与几何测量（红点直径/居中/半径/颜色）
- [x] 4.2 对照现场模板自带的红点位置：自绘红点与模板红点的落点差（期望 ≤1px）
- [x] 4.3 打包重建（先备份现场）→ 恢复现场 → 打包版复跑红点样式与默认样式；GUI 冒烟

## 5. 文档与归档

- [x] 5.1 `docs/验收清单.md`：定位点判据补「样式可选/红点几何」
- [x] 5.2 `使用说明.txt`：界面说明（勾选框 + 样式下拉）、CLI（`--anchor-style`）、日志行
- [x] 5.3 `docs/汇报/18-无图模板与红点定位点.md`
- [x] 5.4 `openspec validate --strict --all` 全绿；归档 `anchor-red-dot`；中文提交信息分批提交
