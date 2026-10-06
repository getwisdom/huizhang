# 19 flexible-io 实施与装置维护（W1 / W2 / W3 + 维护①②③）

- 汇报日期：2026-10-06（下午场）
- 承接：`docs/汇报/14-产品评审.md` 拍板结论 → 实施 `openspec/changes/flexible-io`（已归档）；另做装置维护三项。
- 提交序列（全部中文提交，提交前均 `git status` 核对；未用 `git add -A`）：
  - W1 文档批 `4a2e54c` → W2 实现批 `34d078b` → W3 验收与归档 `eb11feb`
  - 装置维护①夹具解耦 `dfd87e3` → ②11 号存档行 `65c549e` → ③无图模板入库 `d61e9a9` → 本报告（见 `git log`）

---

## ① 任务与范围

**flexible-io（按 tasks.md 的 W1→W2→W3）**
- W1 文档批：验收清单新增 A/B 组判据与阶段 4 追加；`使用说明.txt` v1.1（新增「五、自定义目录」、CLI 调用姿势修正、换批次提示）；README / PROJECT / AGENTS / config 归档措辞修正。
- W2 实现批：GUI 目录选择（可编辑 / 浏览… / 恢复默认、QSettings 四键记忆、运行期锁定、「打开输出目录」跟随）；校验五连（中文报错、任务不启动）；关窗保护（「继续等待 / 取消任务并退出」，修 0xC0000409 崩溃）；共享清理规则（仅默认「已排版」清空，自定义只写不删 + 计数提示）；日志三补（完整路径 / 兜底落盘 / 取消状态行 + 运行前计数）。
- W3：全部新增判据 + 阶段 0.1/0.2/1/2/4 复跑；`openspec archive flexible-io`（归档为 `2026-10-06-flexible-io`，6 条 requirement 合并）；14 号评审追加「已落地」小节。

**装置维护**
1. 抠图夹具解耦：7 张原样本入库 `golden/fixtures/原图/`，`test_cutout_golden` 改读夹具；验收清单阶段 1 输入改夹具、阶段 0.1 改「运行前快照 → 运行后自比对」并刷新参考快照。
2. `docs/汇报/11-产品评审.md` 文首加【存档】行。
3. `无图模板.jpg` 入库为模板回归数据。

**非目标（已保持）**：不改 layout-fit / layout-center / outline-template / anchor-red-dot 既有行为（圆径/圆心实测、样式下拉、细采样回退均未动）；不动目录契约；不引入联网；CLI 创建规则与退出码口径维持现状（差异记录于使用说明，见 ⑤）。

**纪律**：13 个数据目录零改动（数字见 ③）；试验全部在仓库外独立运行目录（`D:\workspace\_koutu_fio_run\`）；禁逐字节 SHA（一律像素指标 + 日志统计行；本报告引用的「逐字节一致」均为既往轮次既有表述，本批未新增）。

## ② 命令 / 操作

**W1（文档）**
- 编辑 6 处文档 → `openspec validate --strict --all`（`cmd /c openspec.cmd …`，乱码看退出码）→ 8/8、退出码 0 → 单独提交。

**W2（实现 + 实跑 + 打包）**
- 代码：`koutu/paths.py`（`is_default_layout_dir`）、`koutu/core/layout.py`（`clean_old`、计数、取消行、异常兜底）、`koutu/core/cutout.py`（计数、取消行、兜底落盘）、`koutu/cli/main.py`、`koutu/gui/dirselect.py`（新）、`koutu/gui/pages.py`、`koutu/gui/main_window.py`、`koutu/gui/worker.py`。
- 测试：`pytest tests -q` → **83 passed, 1 skipped**；新增 `tests/test_gui_dirs.py`（13 例：目录行/记忆回退/五连/运行锁定/打开跟随/自定义只写不删/关窗两路径/无任务关窗）。
- 源码版实跑（副本 `_koutu_fio_run\src-run\`：`koutu` 包 + 7 张原图 + `排版demo.png`）：
  - CLI：`python -m koutu cutout`（默认）/ `cutout --dst "自定义 输出 目录\CLI 抠图"` / `layout --dst "…\CLI 排版"`（预置 `我的照片.png`、`笔记.txt`、`第9页.png`）/ `layout`（默认 `已排版`，预置旧文件）/ `layout --demo 坏模板.png` —— 退出码 0/0/0/0/**1**，日志行见 ③。
  - GUI 驱动 `drive_fio.py`（offscreen、程序根指向副本）：自定义目录跑通两能力、取消收束、关窗保护（`继续等待`/`取消任务并退出` 两路径）。
- 打包：现场备份（217 文件）→ `packaging\打包.ps1` 重建 `dist\koutu\`（**200 文件 / 138.6 MB**）→ 复制为「`koutu v1.1 冒烟`」（中文 + 空格路径）实跑 → 恢复现场（使用者模板 / 无图模板 / koutu.ini / 日志 / 底图 12 / 已排版 2 全部回位；现场 exe 与使用说明已是 v1.1）。
- 打包版实跑：CLI 五例（同源码版清单）＋ GUI（UIA 真机驱动，脚本 `uia_close_drive.ps1` / `uia_wait_drive.ps1` / `uia_custom_drive.ps1` / `uia_cutout_drive.ps1`）——自定义目录、打开输出目录（Explorer `LocationURL` 核验）、记忆复现、关窗两路径。

**W3（验收 + 归档）**
- 阶段 0.2：`hash-tree.ps1 -Base legacy` + `compare-manifests.ps1`（18 文件）。
- 阶段 1/2：副本内 `cutout` 与 `layout --no-anchors` → `pixel-diff.ps1` 对照 `golden/baseline_products`；日志统计行与 `golden/logs/run_final/` 逐项比对（脚本 `w3_stage12_compare.py`）。
- 阶段 0.1：`hash-tree.ps1`（13 目录）→ `compare-manifests.ps1`（冻结清单 + 本批自比对两份）。
- 打包版三路冒烟：自定义目录（CLI + GUI）、关窗保护（两路径）、CLI 姿势复核。
- 归档：`cmd /c openspec.cmd archive flexible-io --yes` → 退出码 0；`validate` 8/8。
- 14 号评审追加「已落地（实施批）」。

**维护①②③**
- ①：`Copy-Item _koutu_golden\原图\*.jpg → golden\fixtures\原图\`；`test_cutout_golden.py` 改读夹具；`.gitignore` 对 `golden/fixtures/原图/` 反忽略（沿用 `baseline_products/底图/` 先例）；验收清单 0.1/阶段 1 改写；刷新参考快照 `golden/checksums/original_data_current_2026-10-06.csv`；`pytest tests -q` → **84 passed, 0 skipped**。
- ②：11 号文首加「【存档】早期版本，已被 14-产品评审.md 取代，仅存查」→ 入库提交。
- ③：`git add 无图模板.jpg`（用例 `test_layout_outline_template.py::test_wutu_template_eleven_slots_and_grid` 已实跑断言 11 槽位/细采样回退；验收清单注明）。

## ③ 关键数字

**校验与测试**
- `openspec validate --strict --all`：归档前 8/8、归档后 8/8（退出码均 0）。
- `pytest tests -q`：W1 前 61 passed + 1 skipped → W2 后 **83 passed, 1 skipped** → 维护①后 **84 passed, 0 skipped**（skip 修复 +1；其余增加值 = W2 新增用例）。

**阶段复跑（W3）**
- 0.1：本批全操作「运行前快照 → 运行后自比对」**差异数 0**；与冻结 `original_data_after.csv` 对比差异 26 条，**全部集中在 `原图 / 底图`**（使用者 2026-10-06 自换批次，属使用者操作，非本批引入）；其余 11 目录 0 差异。
- 0.2：`legacy\` 18 文件，**差异数 0**。
- 阶段 1：7/7 张 `alpha>8=0、maxAlphaDiff=0、rgb>8=0`；opaque 逐张相等；圆心/半径与基线差 **0px / 0px**；退出码 0。
- 阶段 2：`已排版\第1页.png` 2480×3508；opaque 8,699,840 逐值相等；`rgbDiff>8=1146（0.0132% ≤0.5%）`、`alphaDiff>8=0`；分配表 **7 行逐行一致**；关键行（模板 2480x3508 / 识别到 11 个槽位 / 共 1 页 / 定位点: 已关闭）齐备；退出码 0。
- 打包版窗口出现耗时：**597 ms**（本轮三次 UIA 测量 585 / 574 / 597 ms；较首轮评审记录的 193–280 ms 偏慢，原因见 ⑤）。

**打包版三路冒烟（关键行原文）**
- 自定义（CLI）：`cutout --dst "自定义 输出 目录\CLI 抠图"` 7/7、退出码 0；`layout --dst "…\CLI 排版"` 退出码 0，`我的照片 = 笔记 = 第9页 = True、第1页 = True`；日志 `运行前: 有效底图 7 张；同名覆盖 0 个；检测到本工具旧页 1 张（自定义输出目录，不清理）`。
- 自定义（GUI/UIA）：输出目录改 `…\自定义 输出 目录\UIA 排版` → 2 页产物；日志 `（自定义输出目录，不清理）`；`打开输出目录` → Explorer `file:///…/UIA 排版`；`koutu.ini` 含自定义值；重启复现 = True；另测抠图页自定义（2 产物）——两能力均跑通；两次关闭退出码均 0。
- 关窗保护（UIA）：对话框按钮 `关闭 | 继续等待 | 取消任务并退出`；「取消任务并退出」→ 收束后关闭、**退出码 0**、日志 `已取消：已生成 1/2 页`（旧版 0xC0000409 崩溃不再出现）；「继续等待」→ 任务照常完成、随后正常关闭退出码 0；无任务关窗退出码 0。
- CLI 姿势：cmd 直调等待、输出可见、`ERL=1`（坏模板，耗时 0.14 s）/`ERL=2`（watermark）；PowerShell 裸调用 **2 ms 即返回、`$LASTEXITCODE=[0]` 失真**；`Start-Process -Wait` ExitCode=2。与 `使用说明.txt` v1.1 表述一致。
- 坏模板（源码 & 打包）：退出码 1、日志落盘且含 `错误: 模板文件打不开：…（不是有效的图片，或文件已损坏）`、无 `cannot identify` 英文原文。

## ④ 产物清单

**仓库（已提交）**
- 代码：`koutu/paths.py`、`koutu/core/layout.py`、`koutu/core/cutout.py`、`koutu/cli/main.py`、`koutu/gui/dirselect.py`（新）、`koutu/gui/pages.py`、`koutu/gui/main_window.py`、`koutu/gui/worker.py`。
- 测试：`tests/test_gui_dirs.py`（新）、`tests/test_gui_smoke.py`、`tests/test_paths.py`、`tests/test_layout_unit.py`、`tests/test_cutout_unit.py`、`tests/test_cli_layout.py`、`tests/test_cutout_golden.py`。
- 规格：`openspec/specs/{badge-layout,desktop-gui,pipeline-orchestration}/spec.md`（合并）；`openspec/changes/archive/2026-10-06-flexible-io/`（原 change 全套）。
- 文档：`docs/验收清单.md`（阶段 4 追加、阶段 5 A/B、0.1/1 改写）；`使用说明.txt`（v1.1）；`README.md` / `PROJECT.md` / `AGENTS.md` / `openspec/config.yaml`；`docs/汇报/14-产品评审.md`（已落地）；`docs/汇报/11-产品评审.md`（存档行）。
- 数据：`golden/fixtures/原图/`（7 张）；`golden/checksums/original_data_current_2026-10-06.csv`；`无图模板.jpg`；`.gitignore`（+2 行）。

**运行目录（仓库外，未入库）**
- `D:\workspace\_koutu_fio_run\`：`src-run\`（源码副本）、`koutu v1.1 冒烟\`（打包副本）、`pack_backup\dist_koutu_现场_2026-10-06\`（现场备份 217 文件）、`evidence\`（本报告引用的全部 stdout/日志/截图工件与 `*_summary.txt`、`posture.txt`、`p6/p7/p8/p9` UIA 记录）、脚本集（`drive_fio.py`、`src_cli_evidence.py`、`pack_cli_evidence.py`、`p5c_batch.py`、`w3_stage12_compare.py`、`uia_*.ps1`、`posture_evidence.py`）。
- `dist\koutu\`：已重建为 v1.1 并恢复现场。

## ⑤ 未验证与风险

- **远端推送**：`git push origin main` 本批共 4 次尝试均失败（`Recv failure: Connection was reset` / `Could not connect to server` 超时；GitHub 线路时通时断）；**本地已全部提交、领先远端 15 个提交**，待线路恢复后补推或由使用者代推。
- **UIA 关窗驱动的细节**：打包版 GUI 用 UIA 真机驱动（与真人操作等价路径：按钮点击、文本框输入、WM_CLOSE/点 X）；`WindowPattern.Close()` 会因模态确认框同步等待超时而不可用，驱动改用 `CloseMainWindow`/`PostMessage(WM_CLOSE)`；脚本留在运行目录可复跑。未做「人手鼠标」逐步截图二次核对（上轮评审已有人工流程截图先例）。
- **无权限校验**：以「临时文件试写探测」实现；未在真实 ACL 受限目录上实测（测试用探测桩模拟返回不可写）。
- **窗口耗时 574–597 ms**：比首轮评审的 193–280 ms 慢，疑似本机长会话负载/杀软实时扫描；未发现与代码路径相关的回归指标（功能判据全过）。
- **环境提示（非产品缺陷）**：控制台 `chcp=65001` 时，cmd 读 GBK 编码的 `.cmd` 批处理会乱码导致参数错乱；产品自身中文输出正常（直调、批处理在 CP936 下均正常）。
- **「61 passed」口径**：维护①的验收文字为「61 passed, 0 skipped」；按期实测为 **84 passed, 0 skipped**——差异 = W2 新增 22 项用例 + skip 转 pass 1 项；无其他解释项。
- **CLI 与 GUI 的规则差异（有意保留）**：CLI 对 `--dst` 缺失仍多级自动创建、退出码口径不变；差异已写入 `使用说明.txt`（三、五节），未改 CLI 行为（design D7）。

## ⑥ 待确认问题

1. **推送**：网络恢复后是否需要我继续补推（或由使用者在网络可用时 `git push origin main`）——本地已全部提交，领先远端 **15** 个提交（截至本报告提交时；已重试 3 次均超时）。
2. **发布目录命名**：是否把 `dist\koutu\` 另存/改名为「koutu v1.1」发布（本批仅重建与冒烟副本使用该名；仓库文件未动）。
3. **0.1 参考快照**：已刷新为 `original_data_current_2026-10-06.csv`（含使用者 2026-10-06 批次；`原图 / 底图` 的 26 条与冻结清单差异均系使用者操作）。是否需要另存一份「干净基准」（如清空 原图/底图 后）由使用者拍板。
4. **坏模板等业务错误退出码**：由原异常路径（未落盘）改为 1 + 中文错误 + 日志落盘；如需维持 `2` 口径请示意。
5. **11 号评审处置**：已按【存档】处理；若需合并进 14 号或删除，请示意。

---

—— 版本 v1.1（2026-10-06）· 相关提交：`4a2e54c` / `34d078b` / `eb11feb` / `dfd87e3` / `65c549e` / `d61e9a9` / 本报告 · 证据目录：`D:\workspace\_koutu_fio_run\evidence\` · 推送状态：4 次尝试失败（线路不通），待恢复后补推
