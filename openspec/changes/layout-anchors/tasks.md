# Tasks —— layout-anchors（排版定位点）

> 门禁：本文件在提案批准（停1）后执行；每波完成即提交（中文提交信息；只 `git add` 本变更明确写入的路径）。
> 验收容差唯一来源：`docs/验收清单.md` 与各能力规格。

## 1. 排版内核（定位点补丁 + 开关 + 日志 + 降级）

- [x] 1.1 `core/layout.py`：定位点窗口常量与补丁提取（相对槽位中心 40×19px；源 = 目标同坐标）与「含底」叠加（每槽位、含空槽；徽章合成之后）；验证：单测——对 `排版demo.png` 断言输出页 11 个槽位窗口区域与模板同区域逐像素相等（`tests/test_layout_anchors.py`，11/11 通过）
- [x] 1.2 `core/layout.py`：`anchors` 开关参数（默认 True）与关闭路径（零绘制）；验证：单测——关闭时窗口区域无搬运痕迹（空槽留白 / 徽章原样），开启时为相等
- [x] 1.3 `core/layout.py`：降级检测（窗口内 min<96 计数 ≥60 视作有标记；否则跳过）与日志行（开启数量行 / 降级句 / 关闭句）；验证：小模板（无标记）不报错且日志含跳过句；关闭运行日志含「已关闭」；既有统计行不变
- [x] 1.4 `core/layout.py`：样张用「去底」叠法（alpha = 255 − min(R,G,B)，≥235 视为 0）仅供对照与定稿；验证：单测——含底 / 去底两版补丁断言（去底版背景角像素纯白、笔画仍在）
- [x] 1.5 实跑核对：独立运行目录（`D:\workspace\_koutu_layout_anchors_run`）跑 CLI（开 / 关各一次）；验证：分配表与 golden 语义一致、开启 vs 关闭差异仅限 11 个窗口（窗口外 0 像素）、退出码 0

## 2. CLI（--anchors / --no-anchors）

- [x] 2.1 `cli/main.py`：`layout` 增加 `--anchors / --no-anchors`（`BooleanOptionalAction`，默认开启，中文 help）；验证：pytest——默认与 `--no-anchors` 各一用例（日志 / 退出码 0）
- [x] 2.2 实跑核对：CLI 两种开关各跑一次并贴日志；验证：`--help` 中文可读（`--no-anchors 关闭`）、退出码 0

## 3. GUI（勾选框 + 记忆 + 运行中禁用）

- [x] 3.1 `gui/pages.py` 增「添加定位点」勾选框（默认勾选）并与 `set_busy` 联动禁用；`gui/main_window.py` 读写设置键 `layout/anchors`；`gui/worker.py` 透传内核；验证：offscreen 单测——默认勾选、记忆回环、运行中禁用 / 结束恢复，全通过
- [x] 3.2 实跑核对：offscreen 端到端（勾选 / 取消各一跑）核对日志与页面；验证：日志含数量行 / 「已关闭」行（`test_gui_smoke.py`）

## 4. 对照样张（停2 交付物）

- [x] 4.1 生成三张对照样张：开启-含底 / 开启-去底 / 关闭（+ ×8 放大对照；独立运行目录 `D:\workspace\_koutu_layout_anchors_run\样张\`）；验证：尺寸 2480×3508、差异仅限 11 个窗口
- [x] 4.2 整理实测数字随样张交使用者目检（停2）；验证：2026-10-06 使用者目检结论 =「按含底收敛（保持默认）」；数字与结论记录于 `docs\汇报\15-排版定位点.md`

## 5. 验收口径与文档

- [x] 5.1 `docs/验收清单.md`：阶段 2 回归命令补 `--no-anchors`、新增「定位点判据」小节；验证：命令按文档逐条可执行（源码版实跑已按此执行）
- [x] 5.2 `使用说明.txt` + `README.md`：排版页勾选框与 CLI 开关说明；验证：文案与实际行为一致（随打包冒烟复核）

## 6. 回归、打包与归档

- [ ] 6.1 全量回归：`pytest tests -q`（当前 50 passed, 1 skipped——跳过项为 cutout golden「源图缺失」，系会话前外部数据替换所致、基线同况）、`openspec validate --strict --all`、阶段 0.1 / 0.2、阶段 2 复跑（关闭 = 基线一致、开启 = 新判据）；数字留档 `docs\汇报\15-排版定位点.md`
- [ ] 6.2 打包更新：`packaging\打包.ps1` 重建 `dist\koutu\`（含 使用说明.txt + 排版demo.png）；中文 + 空格路径冒烟（GUI 三页签 / 退出、CLI 开 / 关各一页、退出码 0/1/2 契约）；数字留档
- [ ] 6.3 `openspec archive layout-anchors` 归档（合并 3 份 delta）并复验 `openspec validate --strict --all`
- [ ] 6.4 `docs\汇报\15-排版定位点.md`（六节）与提交（仅本变更明确写入的路径）
