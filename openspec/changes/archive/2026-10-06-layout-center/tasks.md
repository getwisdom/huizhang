# 任务：layout-center

## 1. 实现

- [x] 1.1 `koutu/core/layout.py`：新增常量 `DISC_WHITE=246`、`DISC_RUN=3`、`DISC_ANGLES=720`、`DISC_TRIM=3.0`、`DISC_ROUNDS=3`、`DISC_OUT_SPAN=60`、`DISC_IN_SPAN=170`、`DISC_SCAN_MAX=470`、`DISC_SCAN_MIN=150`、`DISC_MAX_SHIFT=40.0`、`DISC_MIN_SHIFT=1.0`、`DISC_MIN_RATIO=0.5`
- [x] 1.2 新增 `_measure_slot_center(template_rgb, slot) -> tuple[float, float]`（边界点采样 → 质心初值 → 截尾 Kåsa 3 轮 → 回退规则）
- [x] 1.3 `_render_slot_patch` 增加 `center` 关键字参数（默认 `None` = 检测圆心），`dest_x/dest_y` 改用该中心
- [x] 1.4 `run_layout_batch`：计算 `centers` 与 `radii`，徽章合成传 `center=centers[i]`，定位点传 `centers[i]` / `radii[i]`
- [x] 1.5 日志：新增「圆盘实测」行（槽位数 / 圆径范围 / 圆心最大修正）；槽位分配表打印实际使用的圆心坐标

## 2. 测试

- [x] 2.1 新增 `tests/test_layout_center.py`：
  - 入库旧模板：实测与检测一致（≤0.16px）⇒ 沿用检测圆心
  - 合成「白底 + 圆盘 + 粘连花瓣条」模板：实测圆心把被推偏 30px 的检测圆心校正回真值（≤1px），亚像素偏差不改动
  - 回退路径：纯白整页 / 孤立小块（候选不足）/ 圆盘内半径 60px 小图案 ⇒ 回退检测圆心，不报错
  - 徽章与定位点同源：整批跑通（实色圆质心 = 实测圆心 ≤1.5px；开/关差异横向中点 = 实测圆心；标记顶端贴实测圆外缘）
  - 日志含「圆盘实测」行与实测圆心坐标
- [x] 2.2 复核 `tests/test_layout_anchors.py`（标记区域仍全含标记）与 `tests/test_cli_layout.py`
- [x] 2.3 `.venv\Scripts\python.exe -m pytest tests -q` → **54 passed, 1 skipped**；`test_layout_golden.py` 对照 `rgb>8=1141（0.0131%）`、`alpha>8=0`、`maxAlphaΔ=0`（与改动前逐值一致）

## 3. 实跑与像素证据

- [x] 3.1 独立运行目录 `_koutu_run_center`（现场数据副本）跑源码版：日志 `圆盘实测: 11 个槽位 圆径 412.0~412.0 圆心修正 ≤15.9px`；RANSAC 复测徽章圆心 vs 模板圆盘圆心 **10.11px（最大 16.41）→ 0.95px（最大 1.26）**；半径差 ±0.24px 内
- [x] 3.2 开 / 关定位点差异 **5081 像素**，全部落在 11 个标记区域内（每区 450~472 px，区外 0）
- [x] 3.3 打包（先备份现场 17 文件）→ `packaging\打包.ps1` 退出码 0（200 文件 / 138.6 MB）→ 恢复现场 → 打包版 `koutu.exe layout` 退出码 0，第 1/2 页与源码版**逐字节一致**
- [x] 3.4 GUI 冒烟：窗口 193 ms 出现「koutu · 徽章处理工具」、关闭退出码 0；CLI `layout` 退出码 0

## 4. 文档与归档

- [x] 4.1 `docs/验收清单.md`：阶段 2 增补「圆盘圆心实测校正（layout-center）」判据；阶段 4 增补 layout-center 复跑数字
- [x] 4.2 `docs/汇报/17-排版圆心实测对齐.md`：问题、证据数字、方案、验证结果、遗留
- [x] 4.3 `openspec validate --strict --all` 全绿（含 `flexible-io` 不因本次归档过期）
- [x] 4.4 归档 `layout-center`；按中文提交信息分批提交（只 `git add` 明确路径）
