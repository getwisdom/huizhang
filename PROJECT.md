# Project Context

## Purpose

`koutu`（徽章图片处理）是一套**单机、离线优先的徽章图片批处理工具**。

它把一批拍摄/收集来的徽章照片，处理成可以直接付印的排版页：

1. **抠图** — 自动识别照片中间的圆形徽章，裁出透明背景 PNG；
2. ~~**去水印**~~（已取消）— 水印处理交操作者用豆包等外部工具在程序外人工完成；
3. **排版** — 按模板图上自动识别出的圆形槽位，排成多页 A4 尺寸 PNG。

**当前状态（2026-10-06 起）**：仓库正在按 OpenSpec 提案 `python-pyqt-rewrite` 完全重写为
**Python + PyQt6 单程序**（一个主窗口两个页签 + CLI 子命令），交付 PyInstaller 单目录绿色包。
实施进度见 `openspec/changes/python-pyqt-rewrite/tasks.md`；旧实现已整体归档 `legacy/`（只读参考、不参与验收）。
行为对照的基线是 `golden/` 冻结物，对照命令与容差见 `docs/验收清单.md`。

面对的使用者是不写代码的操作人员：把整个目录拷到任意 Windows 电脑，双击 `koutu.exe` 就能跑，
不需要装 Python、PowerShell 模块、Office 或任何第三方运行时。

## Tech Stack

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 桌面 GUI / CLI | Python 3.12 + PyQt6 | 单程序两页签；CLI 子命令（cutout / layout） |
| 图像算法 | numpy + Pillow | 抠图（扫描 + RANSAC）、排版（连通域槽位识别 + 合成）（水印不在程序内） |
| 打包 | PyInstaller（`--onedir --windowed`） | 单目录绿色包，`_internal/` 与 exe 必须整包分发 |
| 测试 | pytest | 对照用例挂接 `golden/` 金标准 |
| 环境 | 仓库内 `.venv`（Python 3.12.10） | 依赖精确锁定在 `requirements.txt` |

**没有的东西**（不要假设它们存在）：.NET / csc.exe / PowerShell 版实现（已归档 `legacy/`）、
跨平台支持、联网依赖、CI。

## Project Conventions

### 目录即接口

每个处理阶段读写固定的中文名目录，目录名硬编码在参数默认值里（不可重命名）：

- 输入 `原图\` / 输出 `底图\`（抠图）
- `底图\` 之后的去水印环节不在程序内（交外部人工处理）
- 输入 `底图\` + `排版demo.png` / 输出 `已排版\`（排版）

全部 13 个保留目录名与完整契约见 `openspec/specs/pipeline-orchestration/spec.md`（归档后版本）与
本变更 delta；`doubao`、`无水印底图`、`无水印_精修`、`无水印_AI重绘`、`去水印_预览`、`水印诊断`、
`原图_去水印` 为保留名（人工/历史用途，不参与自动流程）。

### 程序根定位（可整目录搬迁）

所有入口都以**程序根**为工作根，不依赖当前工作目录：

- 打包版：`Path(sys.executable).parent`
- 源码版：仓库根（`Path(__file__).resolve().parents[1]`）

资源（`排版demo.png`）、日志与设置（`koutu.ini`）都相对该根定位。新增入口必须沿用这条约定。

### 文件即日志

不引入日志框架，固定日志文件（程序根，UTF-8）：

| 文件 | 产出者 |
| --- | --- |
| `运行日志.txt` | 抠图 |
| `排版日志.txt` | 排版（含逐槽位分配表） |

日志同时是**验证证据**：里面记录每张图的输出尺寸、圆心、半径、页数与槽位映射。

### 内存内位图处理

图像算法一律用 numpy 数组操作像素（不用逐像素 Python 循环），因为要处理 2480×3508 量级的画布。

### 中文优先

面向操作者的提示语、日志、注释、文档全部用中文。文件编码：`.py / .md / .txt` 保存为 UTF-8；
`.ps1` 保存为 UTF-8 **带 BOM**；若保留 `.bat` 用系统 ANSI（GBK）并在开头 `chcp 65001`。

### 输出覆盖同名文件

各阶段输出同名 `.png` 并直接覆盖，不做备份、不加时间戳。`已排版\` 例外：每次运行先清空旧 PNG。

## Architecture Patterns

### 三层：core / CLI / GUI 单一实现

- `koutu/core/`：两个能力内核 + 批次执行器（纯逻辑，不 import Qt）
- `koutu/cli/`：argparse 子命令（`cutout / layout`）+ 统一退出码（0/1/2）
- `koutu/gui/`：PyQt6 单窗口两页签（后台线程、进度、取消、QSettings 记忆）

旧世界的「算法内核 + 双实现」已终止：双实现同步义务随重写结束，等价性由 `golden/` 回归保障。

### 参数集中在入口

可调参数只在 `argparse`（CLI）与 GUI 控件里声明一次，不散落在算法体内。
抠图参数（扫描阈值 45 / 羽化 4 / 边距 4）沿用旧范围；排版参数由模板与底图决定。

### 确定性

抠图 / 排版的随机性使用固定种子，可复现（同输入同参数同输出）。

### 稳健拟合优于精确阈值

圆形定位沿用「扫描/连通域拿到候选点 → RANSAC 剔除干扰点 → 最小二乘精修」的既有策略。

## Domain Context

- **徽章**：圆形金属徽章（珐琅/蚀刻）。实拍照片背景杂乱，圆形之外可能还有飘带、边框、角落图案。
- **水印（已移出程序范围）**：照片上的淡色平铺水印由操作者用豆包等外部工具人工处理；W3 测绘结论留档 `docs/水印研究.md`（不采用）。
- **模板**：`排版demo.png`，A4 300dpi 竖版 2480×3508 白底图，上面印有圆形徽章槽位图案（当前 11 个）。
  换版面 = 换这张图，`每页张数` 由模板上的圆的个数决定。

## Important Constraints

- **仅 Windows**：工具链与交付物都面向 Windows 10/11；不做跨平台（见提案非目标）。
- **圆内必须完整不透明**：圆形区域内的白色文字、浅色纹样都要保留，不能出现空洞或半透明。
- **只支持完整圆形徽章**：非圆形徽章不适用。
- **输出尺寸与模板一致**：排版页必须等于模板尺寸（2480×3508，白底）。
- **透明通道必须保留**：抠图输出（含羽化带）的 alpha 语义不可被后续环节破坏。
- **无联网依赖**：运行期不依赖任何网络服务。
- **不使用破坏性快捷键操作**：处理是批量覆盖写的，运行前应确认输出目录内容可弃。

## External Dependencies

| 依赖 | 用途 | 缺失时的行为 |
| --- | --- | --- |
| Python 3.12.10（仓库 `.venv`） | 源码运行与构建（开发机） | 交付包（PyInstaller）不依赖系统 Python |
| PyQt6 / numpy / Pillow | GUI 与图像算法 | 版本见 `requirements.txt`（精确锁定） |
| PyInstaller | 构建绿色包 | 只能源码运行（用 `.venv` 解释器） |
| ~~本地 ComfyUI / 豆包在线~~ | 旧 AI 去水印路线 | 非目标；水印改用豆包等外部工具人工处理（程序外；`legacy/remove_watermark_ai.py` 仅历史参考） |

## 构建 / 运行命令

```powershell
# 源码运行（开发；koutu/ 包在 W1–W5 波次落地，以下为既定目标形态）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu              # GUI（两页签）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu cutout       # CLI 抠图（批处理）
& D:\workspace\koutu\.venv\Scripts\python.exe -m pytest tests -q    # 测试（挂 golden）

# 打包（W5 起；脚本 packaging\打包.ps1 或下面这条模板命令）
& D:\workspace\koutu\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed `
  --name koutu --specpath packaging koutu\__main__.py

# 旧工具（只读参考，位于 legacy\；不要当作验收基准）：
#   legacy\抠图.bat / legacy\排版.bat 等仍可手动运行，但产物对照一律以 golden\ 为准
```

> 设计依据：`openspec/changes/python-pyqt-rewrite/design.md`（D1 分层 / D7 打包）；环境实测数据：`docs/环境验证.md` §5–6。
