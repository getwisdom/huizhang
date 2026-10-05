# Design —— python-pyqt-rewrite（koutu 完全重写）

## Context

- 现状：旧工具集 = C# 双实现（两个 exe）+ PowerShell 脚本版（`Add-Type` 内联同一套 C#）+ Python 去水印三路线 + 五个 `.bat` 入口；三套独立 GUI；无 git 时代的验收靠日志统计行与探针脚本。
- 已就绪的前置：`golden/`（双实现逐字节一致、原仓库零改动、像素级对照脚本与容差草案）、`docs/环境验证.md`（Python 3.12.10 / PyQt6 6.11 / PyInstaller 6.22.3 实测，含中文+空格路径、§7 编码坑、§9 交接要点）、`docs/验收清单.md`（阶段 0–4 判据）、`requirements.txt`（精确锁定）、git（2 个提交、身份 `koutu <koutu@localhost>`）。
- 本设计对应规格：本变更 7 份 delta（`badge-cutout / badge-layout / watermark-removal / pipeline-orchestration / diagnostics / desktop-gui / packaging-toolchain`）。动机与范围见 `proposal.md`。
- 补交材料（会话中途落地）：`docs/基线知识.md` 与 `docs/金标准数据.csv` 已逐项对照：抠图/排版参数语义与本文档一致；排版槽位排序已按「包围盒顶边 y → 左边 x」在规格中收紧；`原图_去水印` 等历史目录归入保留名单。

## Goals / Non-Goals

**Goals：**
- 一个可交付目标：单程序（GUI 三页签 + CLI 子命令共享一个核心库），PyInstaller 单目录绿色包。
- 抠图、排版按旧参数语义重写，验收全部挂接 `golden/`（容差口径以 `docs/验收清单.md` 与规格为准）。
- 去水印从零设计：确定性、离线、alpha 逐像素不动；量化指标在 W3 定稿后才签收。
- 仓库结构收敛：旧实现进 `legacy/`（只归档不删除），验收装置（`docs/`、`tests/`、`golden/`）入库。

**Non-Goals（设计层）：**
- 不做跨平台抽象层、不做插件化/可配置化改造、不重构 `golden/` 与验收装置本身（复用）；
- 不追求与旧实现逐字节一致（按容差验收，见 Risks）；
- 不动任何数据目录、不改写 git 历史。

## Decisions

### D1 分层：core / cli / gui 三层，单一执行路径

```
koutu/                 # 正式 Python 包（唯一种子的实现）
  __main__.py          # python -m koutu
  app.py               # 入口分发：无子命令 → GUI；有子命令 → CLI
  paths.py             # 程序根、目录契约常量、日志/设置路径
  config.py            # QSettings(IniFormat) 包装 + 参数默认值
  logging_zh.py        # 日志装配（UTF-8、统计行、中文消息）
  core/
    pipeline.py        # 批次执行器：扫描→逐张→回调日志/进度→汇总（唯一执行路径）
    cutout.py layout.py watermark.py   # 三个能力内核（纯逻辑，不 import Qt）
    imaging.py         # numpy/PIL 像素工具（加载、保存、缩放）
    naming.py          # Windows 自然序（StrCmpLogicalW，ctypes）
  cli/main.py          # argparse 子命令 + 退出码
  gui/main_window.py worker.py pages/...   # PyQt6
packaging/             # koutu.spec、打包.ps1（UTF-8 BOM）
legacy/  tests/  golden/  docs/          # 归档 / 装置 / 文档
```

理由：GUI 与 CLI 调同一条 `core.pipeline`，统计行与日志同源渲染，pytest 直接测 `core`；PyInstaller 只打一个入口包。
备选：单文件脚本（拒绝，三能力+GUI 会失控）；按能力拆三个程序/三个包（非目标）。

### D2 执行与取消：协作式批次执行器

- `pipeline.py` 提供「批处理执行器」：遍历输入目录（确定性顺序）→ 逐文件调用对应内核 → 通过回调发出 `日志行 / 进度(done,total) / 单张结果` → 汇总（成功/失败/取消）。
- 取消 = 回调返回 `False` 的协作式取消，**在单张文件边界生效**（当张完成后停止）；GUI 取消按钮与 CLI 都不例外。
- 退出码统一：全部成功 0 / 有文件失败 1 / 未捕获异常 2。

### D3 GUI 线程模型（PyQt6）

- 主线程只做界面；任务在 `QThread` 中运行（Worker 对象 `moveToThread`），信号：`log_line(str)`、`progress(done, total)`、`finished(ok, fail, cancelled)`、`failed(str)`。
- 同一时刻只允许一个任务；运行中切页签不中断任务；取消标志由 GUI 设置、Worker 在单张边界检查。
- 不做多任务并发（避免日志/进度交错，也符合「单程序、一步一任务」的操作者心智）。
- 备选：`QThreadPool/QRunnable`（拒绝：取消与进度语义更绕）；`multiprocessing`（拒绝：打包与启动成本高）。

### D4 日志与设置

- 三份日志固定文件名与位置（程序根，UTF-8）：`运行日志.txt`（抠图）、`去水印日志.txt`（去水印）、`排版日志.txt`（排版，含槽位分配表）。`_layout_log.txt` 退役。
- 统计行 = 内核返回的结构化结果 → 中文行渲染一次，三处同源：GUI 日志视图原文、CLI 控制台（源码版）、日志文件。格式与 golden 基线**语义等价**（数值逐张可核对）。
- 设置用 `QSettings` 的 `IniFormat`：打包版存程序根 `koutu.ini`（不可写时回退 `%APPDATA%\koutu\koutu.ini`）；源码版存仓库根 `koutu.ini`（gitignore）。记忆：窗口几何、上次页签、各页参数（`cutout/scan-t`、`cutout/feather` 等）。
- 备选：Windows 注册表默认存储（拒绝：设置不随绿色包搬迁，违背「拷贝即用」习惯）。

### D5 程序根与资源语义

- `paths.program_root()`：打包版（`sys.frozen`）→ `Path(sys.executable).parent`；源码版 → 仓库根（`Path(__file__).resolve().parents[1]`）。
- 数据目录、日志、`koutu.ini`、`排版demo.png` 全部相对该根定位，不用 cwd、不写死绝对路径；PyInstaller 的 `_internal/` 只承载依赖，不作为资源查找路径。
- `排版demo.png` 是**可替换资源**：打包时拷贝到 exe 同级（不埋进包内），换版面 = 换这张图（沿用旧习惯）。

### D6 旧实现归档（legacy/，只归档不删除）

- 归档对象：`抠图工具.cs / 排版工具.cs / cut_badge.ps1 / layout.ps1 / detex.py / remove_watermark.py / remove_watermark_ai.py / ocr.ps1 / scan_watermark.ps1 / _analyze.ps1 / _probe_demo.ps1`、旧入口 `.bat`（抠图/排版/去水印/去水印AI/豆包流程）、旧 exe（本地移动；`*.exe` 不入库，可由随库 `.cs` 重建）。
- 动作：`git mv`（保留历史）→ 根目录仅余新程序、文档、规格、装置；新增 `legacy/README.md`（历史状态 + 「不参与验收」+ 可只读排查）。
- `golden/tools/` 冻结副本不动；`docs/验收清单.md` 阶段 0.2 的路径与对照方式随归档更新（内容哈希逐文件对应，忽略 `legacy\` 前缀）。
- 时机：W0（批准后的首个波次），此后所有波次在干净根目录上工作；仓库外副本 `D:\workspace\_koutu_golden` 与 `legacy/` 双保险。

### D7 打包策略（PyInstaller onedir，参照环境验证 §5–6）

- 构建：`.venv` 解释器 + `pyinstaller --noconfirm --clean --onedir --windowed --name koutu --specpath packaging`（模板见环境验证 §5.1；已实测 8.6s、142 文件 / 88.5MB）。
- 交付目录：`koutu.exe` + `_internal/` + `排版demo.png` + `使用说明.txt`（后两者构建脚本拷贝到 exe 同级）；`dist/`、`build/`、`*.exe` 不入库。
- CLI 可见性：打包版为 `--windowed`（无控制台）——CLI 验收证据以「日志文件 + 退出码」为准（与旧 winexe 行为一致）；源码版保留控制台输出。控制台孪生 exe 为备选（见 Open Questions）。
- 冒烟口径：中文+空格路径复制后双击（首启 217ms / 热启 143ms 量级）、`PATH` 清理会话模拟无 Python 机器、退出码 0。

### D8 验收如何挂接 golden

| 阶段 | 对照物 | 执行者 |
| --- | --- | --- |
| 0 装置自检 | `golden/checksums/`（数据目录 0 差异；旧工具内容 0 差异，路径映射到 legacy\） | 每次验收前（`golden/scripts/hash-tree.ps1` + `compare-manifests.ps1`） |
| 1 抠图 | `golden/baseline_products/底图/` + `run_final/运行日志.txt`：文件名集合、宽高、圆心/半径 ±2px、不透明像素 ±0.5%、pixel-diff 草案阈值 | pytest（`tests/`）+ 人工命令 |
| 2 排版 | `baseline_products/已排版/第1页.png` + `run_final/_layout_log.txt`：2480×3508 精确、页数、分配表逐行、像素阈值 | 同上 |
| 3 去水印 | **旧输出不作数**；指标由 W3 定稿写入 `docs/验收清单.md` 阶段 3 后签收 | W3 定稿 + pytest |
| 4 打包 | 环境验证 §5–6 实测口径 + 阶段 1/2 判据在打包版复跑 | 人工 + CLI |

- pytest 侧用 numpy 直接实现与 `pixel-diff.ps1` 相同的口径（阈值同源：`docs/验收清单.md`）；`golden/scripts/` 保留给人工与跨机器复验。两套口径的唯一数值来源是验收清单/规格，评审时核对。

### D9 旧规格处置（取代 / 保留语义 / 归档时机）

| 旧规格（5 份） | 处置 | 机械落点（本变更 delta） | 归档时机 |
| --- | --- | --- | --- |
| `badge-cutout` | 全面取代（双实现/脚本版/旧 GUI 退役） | 旧 10 条 REMOVED + 新 8 条 ADDED | 本变更归档时（`openspec archive`） |
| `badge-layout` | 全面取代 | 旧 7 条 REMOVED + 新 6 条 ADDED | 同上 |
| `watermark-removal` | 重新设计取代（AI 路线移除） | 旧 8 条 REMOVED + 新 7 条 ADDED | 同上 |
| `pipeline-orchestration` | 保留语义、载体更新（单程序入口；豆包流程移除） | 旧 5 条 REMOVED + 新 4 条 ADDED | 同上 |
| `diagnostics` | 语义收窄保留（装置升级为 golden 脚本 + pytest；探针归档） | 旧 6 条 REMOVED + 新 3 条 ADDED | 同上 |

- 归档前一律不删旧规格文件；delta 合并（`openspec archive`）一次性完成新旧切换。归档后需修订 5 份主规格中不在需求里的说明文字（Purpose/工具表，见 tasks W6）。

### D10 入库决策：docs / tests / golden（含 docs\汇报\）

现状：`.gitignore` 第 32–38 行整体忽略 `golden/`、`docs/`、`tests/`（「尚未定稿，暂不入库」）。

决策（写入本设计即生效，执行在 W0）：

1. **`docs/` 入库**（全文，含 `docs/汇报/`）：全部为文本，是规格与验收的知识底座；`04-架构师.md` 等汇报随该批入库。
2. **`tests/` 入库**：pytest 装置必须与代码同演进；小文本。
3. **`golden/` 入库**：按 README 定位「入库的冻结精简集」（72 文件 / 约 12.1MB，含 `baseline_products/` 大图——一次性体积成本，换取「克隆即可复验」）；例外维持：`*.exe`（全局规则，按随库源码重建）、`golden/logs/` 中体积可控、全入。
4. **时机**：门禁 B 批准后、实施 W0 的第一个提交批次；执行 = 删除 `.gitignore` 中 `golden/`、`docs/`、`tests/` 三行 + 新增忽略 `dist/`、`build/`、`去水印日志.txt`、`koutu.ini`。
5. 保持忽略不变：13 个数据目录、`运行日志.txt / 排版日志.txt / _layout_log.txt`、`_probe_*`、`*.exe / *.zip / *.7z`、`.venv/`、`__pycache__/`、`.pytest_cache/`、`spike/_out/`。
6. 备选（不推荐）：golden 只入文本、大图留仓库外——会让「克隆即复验」失效，违背验收装置初衷。

### D11 文档更新计划（批准后由 tasks 执行）

| 文档 | 更新内容 | 时机 |
| --- | --- | --- |
| `AGENTS.md` | 硬约束改写：删「双实现同步」「csc.exe 现场编译」「无包管理/测试框架」；新增单实现 + golden 回归 + pytest + PyInstaller；保留中文契约、程序根定位、Windows-only、编码约定；命令表补 pytest/打包命令 | W0 |
| `PROJECT.md` | 技术栈（Python 3.12 + PyQt6 + PyInstaller）、架构模式（三层）、编译命令 → 打包命令、去水印章节（新路线，W3 回填）、「没有的东西」更正（已有 git/pytest/依赖清单） | W0 |
| `openspec/config.yaml` | `context` 改写为重写世界（保留不可改名目录契约、全中文、Windows-only）；`rules.tasks` 的「同步另一侧实现」→「对照 golden 回归」；`operations` 指南更新（apply=pytest+实跑；archive=新规格与实现一致） | W0 |
| `README.md` | 重写为单程序说明（三页签、CLI、打包、目录契约、验收） | W5 |
| `使用说明.txt` | 重写（三能力操作、CLI、常见问题、日志位置）；`排版工具使用说明.txt`、`总结文档.md` 归档 `legacy/docs/` | W5 |

### D12 迁移与回滚

- 操作者迁移：入口从「多个 exe/bat」变为「一个 `koutu.exe`」；日志从三个文件名变为三份固定名（`_layout_log.txt` 退役、新增 `去水印日志.txt`）；AI/在线去水印流程移除（`doubao` 目录保留）。
- 回滚：旧实现完整保留在 `legacy/`（源码可重建 exe；冻结身份在 `golden/tools/` 与仓库外副本）；若重写版验收不达标，可继续使用旧工具直至问题修复。

## Risks / Trade-offs

- **位级一致性风险**（C# 的取样/取整细节 vs numpy 实现）→ 按容差验收（圆心/半径 ±2px、不透明 ±0.5%、像素差草案阈值），W1/W2 逐张记录实测值；不追字节级。
- **打包版无控制台**，CLI 输出不可见 → 证据改为日志+退出码（先例：旧 winexe 实测 stdout 为空、验收照过）；需要可见性时用源码版或备选孪生 exe。
- **QSettings 写程序根失败**（只读目录）→ 回退 `%APPDATA%\koutu\`；测试覆盖两种路径。
- **去水印研究不确定性** → 独立 W3 波次 + 定稿门禁（未定稿不签收阶段 3）；旧输出不作数，避免错锚。
- **大体积图片入库**（golden 约 12.1MB）→ 一次性成本；README 已声明该目录就是入库精简集。
- **归档时机**：W0 移动旧文件后，阶段 0.2 的对照路径需同步更新（内容哈希映射校验），避免「文件搬家」被误判为「工具被改动」。
- **取消语义**在单张边界生效 → 文档与界面文案写清楚，避免误以为立即中断。

## Migration Plan

1. W0：`.gitignore` 修订 → `docs/tests/golden` 入库 → `legacy/` 归档（含验收清单阶段 0.2 更新）→ AGENTS/PROJECT/config 更新；每一步独立提交（中文信息，提交前 `git status` 核对无数据目录/venv）。
2. W1–W4：模块波次实现（抠图 / 排版 / 去水印研究 / GUI），每波带 pytest 对照与实跑核对。
3. W5：打包交付 + 使用说明/README 重写 + 阶段 4 验收。
4. W6：全量回归 → 修订主规格说明文字 → `openspec archive python-pyqt-rewrite` → 最终汇报。回滚点：任一波次不达标即停在当波修复（不回退已验收的前波）。

## Open Questions

- 是否补一个控制台孪生 exe（`koutu-cli.exe`）增强打包版 CLI 可见性？（追加式，不改现有规格与任务；实施期可加）
- 交付文件夹是否带版本号（建议 `koutu v1.0\`）？实施时按运维习惯定，不影响契约。
- 主程序窗口标题与图标文案（`koutu` / 「徽章处理工具」等）：W4 与使用者确认，不影响规格（未要求具体标题词）。
