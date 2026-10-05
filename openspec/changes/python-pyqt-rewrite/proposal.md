# 提案：koutu 完全重写（Python + PyQt6 单程序）

## Why

- 旧工具集由三个技术面拼成：C# 双实现（`抠图工具.cs`→`徽章抠图.exe`、`排版工具.cs`→`排版工具.exe`）、PowerShell 脚本版（`cut_badge.ps1`、`layout.ps1` 用 `Add-Type` 内联同一套 C#）、Python 去水印三路线（detex / 点阵扣除 / AI 重绘）。同一算法两份实现要手工同步，GUI 是三个各自独立的窗口，去水印里 AI 路线已被定案为非目标。维护成本与分叉风险只会继续上涨。
- 前置证据已经齐备：`golden/` 冻结了旧工具行为（抠图/排版双实现逐字节一致、原仓库零改动、像素级对照与容差草案）；`docs/环境验证.md` 实测了 Python 3.12.10 + PyQt6 6.11 + PyInstaller 6.22.3 在中文+空格路径下的打包与双击；`docs/验收清单.md` 给出三阶段判据。现在是把证据变成实现的时候。
- 目标形态：**单程序、两功能页签（抠图 / 排版）、PyInstaller 单目录绿色包**；Windows-only、面向操作者全中文、中文数据目录契约不变。

## What Changes

- **入口收敛（BREAKING）**：`徽章抠图.exe`、`排版工具.exe`、`抠图.bat`、`排版.bat`、`去水印.bat`、`去水印AI.bat`、`豆包流程.bat` 全部退役并归档 `legacy/`；交付一个主程序 `koutu.exe`（双击 = GUI 两页签；命令行 = 子命令批处理）。迁移：新版《使用说明》、`legacy/README` 与 design 的迁移小节。
- **算法单实现**：抠图、排版以 Python 单实现重写，参数语义对齐旧实现（扫描 40 线、阈值默认 45、RANSAC 600 次固定种子、羽化 4px、边距 4px；槽位 step=4、前景阈值 60、合并 IoU 0.3、半径下限 300、Windows 自然序）。验收挂接 golden 容差（圆心/半径 ±2px、不透明像素 ±0.5%、alpha 差>8 占比 ≤0.5% 等）。「双实现同步」义务随本重写终止。
- **去水印取消（2026-10-06）**：水印处理交操作者用豆包等外部工具人工完成，程序不提供去水印功能（无页签 / 无子命令 / 无内核）；旧 `detex.py` / `remove_watermark.py` / `remove_watermark_ai.py` 及 AI/在线路线整体作废归档。W3 研究（`docs/水印研究.md`）留档不采用；阶段 3 验收取消（旧输出不作数）。
- **日志与证据**：`运行日志.txt`（抠图）、`排版日志.txt`（排版，含槽位分配表）固定在程序目录；`_layout_log.txt` 退役、`去水印日志.txt` 不再新增（去水印取消）。统计行保持可核对语义。
- **装置与文档**：`tests/`（pytest）扩展为金标准回归装置；`docs/`、`tests/`、`golden/` 解除忽略并入版本库（策略见 design.md）；AGENTS.md / PROJECT.md / `openspec/config.yaml` / README / 使用说明 更新；`总结文档.md` 归档。以上文档改动经批准后由 tasks 执行。
- **打包**：PyInstaller `--onedir --windowed` 单目录包（实测 142 文件 / 88.5MB、中文+空格路径可双击），随包携带可替换的 `排版demo.png`，首次运行自动创建数据目录。

### 非目标（Non-Goals）

- 去水印整体不做（含确定性本地路线与 AI/在线路线）——水印由操作者用豆包等外部工具人工处理，相关入口与规格一并移除；
- 跨平台（不做 macOS/Linux，不抽平台适配层）；
- 拆成三个独立程序（三个能力共享一个程序与一套核心库）；
- 不重命名、不迁移、不清理任何数据目录（`原图 / 底图 / 无水印* / 已排版 / doubao` 等 13 个目录名保持原样）；
- 不改写已提交的 git 历史。

## Capabilities

### New Capabilities

- `desktop-gui`: 单主窗口两页签（抠图/排版）、后台线程与进度、取消、QSettings 记忆、全中文界面、统计行展示与「打开输出目录」。
- `packaging-toolchain`: Python 环境与依赖锁定、PyInstaller 单目录绿色包、pytest 装置、编码约定、旧实现 `legacy/` 归档。

### Modified Capabilities

- `badge-cutout`: 旧 10 条需求全部移除（双实现/脚本版/旧 GUI 等退役），新增 Python 抠图内核需求（扫描、RANSAC、羽化裁切、日志、CLI、golden 判据）。
- `badge-layout`: 旧 7 条需求全部移除，新增 Python 排版内核需求（槽位识别、自然序填充、合成、日志、CLI、golden 判据）。
- `watermark-removal`: 旧 8 条需求全部移除（含 AI 两条）；新增「去水印不在本程序范围内（交外部人工处理）」的范围边界需求与 W3 研究留档声明。
- `pipeline-orchestration`: 语义保留、载体更新——目录契约与日志要求改写为单程序版本；旧 `.bat` 入口与豆包衔接流程移除。
- `diagnostics`: 旧探针需求移除（脚本归档 `legacy/` 可只读使用），新增金标准验收脚本口径与排查产物规范。

> 旧 5 份规格的处置策略（取代 / 保留语义 / 归档时机）见 design.md「旧规格处置」，机械落点即本变更的 5 份 delta：归档本变更时一次性完成新旧切换。

## Impact

- 新增：`koutu/`（正式 Python 包）、`packaging/`（打包脚本与 spec）、`legacy/`（归档）、tests 扩展、`dist/`（构建产物，不入库）。
- 变更：AGENTS.md、PROJECT.md、`openspec/config.yaml`、README.md、使用说明.txt、排版工具使用说明.txt；`openspec/specs/` 五份规格在本变更归档时切换到新世界。
- 保持：13 个中文数据目录、`golden/` 冻结物、git 历史、仓库外副本 `D:\workspace\_koutu_golden`。
- 验收影响：阶段 1/2 可量化对照 golden；阶段 3（去水印）已取消（不在范围）；阶段 4 打包验收按 `docs/环境验证.md` §5-6 与 `docs/验收清单.md` 执行。
