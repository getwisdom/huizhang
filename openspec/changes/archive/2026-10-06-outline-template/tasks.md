# 任务：outline-template

## 1. 实现

- [x] 1.1 `koutu/core/layout.py`：`_connected_components(mask, step=STEP)`（包围盒按传入步长放大，默认不变）
- [x] 1.2 拆出 `_detect_slots_step(template_rgb, step)`；新增 `detect_slots_ex()` → `(槽位, 步长)`；`detect_slots()` 改为包装（先 4，空则 2）；新增常量 `DETECT_FALLBACK_STEP = 2`
- [x] 1.3 `run_layout_batch`：改用 `detect_slots_ex`；回退时日志行追加「（细采样回退：步长 2）」
- [x] 1.4 确认其余逻辑零改动（半径/圆心实测、排序、报错语义）

## 2. 测试

- [x] 2.1 新增 `tests/test_layout_outline_template.py`：
  - 合成「白底 + 细圆环（3~3.5px）」模板：`detect_slots` 得 1 槽位，圆心/半径正确；`detect_slots_ex` 返回步长 2
  - 合成模板在主路径可用时（如粗圆环/实心盘）：`detect_slots_ex` 返回步长 4
  - 仓库根存在 `无图模板.jpg` 时实跑：11 槽位、实测圆心与现场模板一致（否则跳过）
- [x] 2.2 回归：`tests/test_layout_golden.py`（`rgb>8=1141（0.0131%）`）、`tests/test_layout_anchors.py`、`tests/test_layout_center.py`、`tests/test_cli_layout.py`
- [x] 2.3 `.venv\Scripts\python.exe -m pytest tests -q` 全绿

## 3. 实跑与像素证据

- [x] 3.1 独立运行目录用 `无图模板.jpg` 跑源码版排版（12 张真底图）：11 槽位、2 页、日志含回退标注；贴统计行
- [x] 3.2 与现场模板的输出对照：徽章圆心/半径一致（圆心差 ≤1px）；记录耗时
- [x] 3.3 回归实跑：现场模板照旧（槽位/分配表/像素数字与上一次一致）

## 4. 文档与归档

- [x] 4.1 `docs/验收清单.md`：阶段 2 增补「空心圆环模板」判据
- [x] 4.2 `docs/汇报/18-无图模板与红点定位点.md`：问题、证据、方案、验证、遗留（第 5 排排序差异）
- [x] 4.3 `openspec validate --strict --all` 全绿（含 `flexible-io` 不因本次归档过期）
- [x] 4.4 归档 `outline-template`；中文提交信息分批提交（只 `git add` 明确路径）
