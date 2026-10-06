# 提案：outline-template —— 只画圆环轮廓的模板（圆内无图）也能识别槽位

## Why

- 使用者指出：**「无图模板也是模板，只是没有图片」**——`无图模板.jpg`（2462×3503，与现场模板同版式：圆内空白、圆外一圈细黑圆环）当前识别 **0 槽位**，会直接报「模板上没有识别到圆形槽位,请检查 排版demo.png」。
- 根因（实测，`probe_v25/v26`）：STEP=4 降采样 + 4 邻域连通域下，**细圆环（约 3~4px 宽）被打散**——721 个连通域，最大仅 217 个采样点（< `MIN_REGION_PIXELS=300`）→ 全部丢弃 → 0 槽位。改用 STEP=2 重跑同一条流程：连通域 22 个 → 合并出 11 个包围盒（824×846~856）→ **11 槽位**（圆环保持连通）。
- 该模板的圆环位置与现场模板的圆盘完全同源：用 `_measure_slot_center` + `_fit_slot_radius` 实测，11 个圆心与现场模板实测圆心差 ≤0.16px（一处 0.90px），圆径均 412.0 → 徽章可精确落入圆环。

## What Changes

- **连通域放大倍数参数化**：`_connected_components(mask, step=STEP)`（默认仍为 4，既有行为不变）。
- **拆出 `_detect_slots_step(template_rgb, step)`**（原 `detect_slots` 的函数体）并新增 `detect_slots_ex()` → `(槽位, 所用步长)`；`detect_slots()` 保持原签名/返回值：先跑 `STEP=4`，**识别不到任何槽位时**用 `DETECT_FALLBACK_STEP=2` 重跑**同一条**流程（同一前景判据、同一连通域/合并/排序/十字弦/半径门槛）。
- **日志**：回退生效时「识别到 N 个槽位」行追加「（细采样回退：步长 2）」，便于人工核对走了哪条路。
- **回归保障**：主路径结果逐字节不变——旧模板与现场模板在 STEP=4 下仍各识别 11 个槽位（回退不触发）；`golden` 对照与既有用例照旧。
- **实跑**：`无图模板.jpg` → 11 槽位（日志含回退标注）；配合「圆盘圆心实测」得到与现场模板同源的圆心/圆径。

### 非目标（Non-Goals）

- 不改主路径（步长 4）的任何阈值/排序/拟合规则，也不改 4 邻域语义（不做 8 邻域、不做 Hough/圆环专用算法）。
- 不改半径与圆心实测逻辑（`_fit_slot_radius` / `_measure_slot_center` 直接复用）。
- 不改「一个槽位都没识别到时」的报错语义（仍报同一句中文错误）。
- **已知差异（不改，报给使用者）**：`无图模板` 的槽位排序在**第 5 排**（x=2049 与 x=411 两个槽）与现场模板互换——排序规则按规范以「包围盒顶边 y」为准，而两张模板该处装饰不同；徽章↔槽位分配随之不同。规范冻结该规则，本次不动。

## Capabilities

### Modified Capabilities

- `badge-layout`：「模板槽位识别」（新增细采样回退）。

## Impact

- 变更产物：`openspec/changes/outline-template/`（proposal / specs / design / tasks）。
- 实现：`koutu/core/layout.py`（`_connected_components(step=)`、`_detect_slots_step`、`detect_slots_ex`、`detect_slots` 包装、`DETECT_FALLBACK_STEP`；`run_layout_batch` 日志标注）。
- 测试：新增 `tests/test_layout_outline_template.py`（合成空心圆环模板 + 真身 `无图模板.jpg` 可选跳过）；既有 `test_layout_golden.py` / `test_layout_anchors.py` / `test_layout_center.py` 回归。
- 文档/验收：`docs/验收清单.md`（阶段 2 补「空心圆环模板」判据）、`docs/汇报/18-*.md`。
- 交付：`packaging\打包.ps1` 重建 `dist\koutu\`（重建前备份现场），并可选把 `无图模板.jpg` 放入现场供使用者试跑。
- 保持：13 个数据目录、`golden/`、`legacy/`、已归档变更与 `flexible-io` 不动。
