# Project Context

## Purpose

`koutu`（徽章图片处理）是一套**单机、离线优先的徽章图片批处理工具集**。

它把一批拍摄/收集来的徽章照片，处理成可以直接付印的排版页，共三个阶段：

1. **抠图** — 自动识别照片中间的圆形徽章，裁出透明背景 PNG；
2. **去水印** — 去掉叠在画面上的平铺淡色水印（点阵小字、斜线细纹）；
3. **排版** — 按模板图上自动识别出的圆形槽位，排成多页 A4 尺寸 PNG。

面对的使用者是不写代码的操作人员：把整个目录拷到任意 Windows 电脑，
双击 `exe` 或 `.bat` 就能跑，不需要装 Python、PowerShell 模块、Office 或任何第三方运行时。

## Tech Stack

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 桌面 GUI / 批处理 | C# / .NET Framework 4.x + `System.Drawing` + WinForms | 用系统自带 `csc.exe` 现场编译成单文件 exe，最终用户零依赖 |
| 脚本版 | Windows PowerShell 5.1 | 通过 `Add-Type` 内联 C#，与 exe 共用同一套算法 |
| 去水印 | Python 3.11 + numpy + Pillow | 三条独立路线（细纹压制 / 点阵扣除 / AI 重绘） |
| AI 重绘后端 | 本地 ComfyUI（SD 1.5 img2img） | 通过 `http://127.0.0.1:8188` 的 HTTP API 调用，可选 |
| 光学识别 | Windows 内置 WinRT `Windows.Media.Ocr` | 仅用于开发期诊断 |

**没有的东西**（不要假设它们存在）：包管理器、构建系统、依赖清单（`requirements.txt` / `*.csproj`）、
自动化测试、CI、`.git` 版本控制。

## Project Conventions

### 目录即接口

每个处理阶段读写固定的中文名目录，目录名硬编码在脚本参数默认值里：

- 输入 `原图\` / 输出 `底图\`（抠图）
- 输入 `底图\` / 输出 `无水印\`、`无水印_细纹轻\`、`无水印_细纹重\`（去水印）
- 输入 `底图\` / 输出 `已排版\`（排版）

管线中每个目录的完整契约见 `openspec/specs/pipeline-orchestration/spec.md`。

### 脚本自定位（可整目录搬迁）

所有入口都以**自身所在目录**为工作根，不依赖当前工作目录：

- C#：`AppDomain.CurrentDomain.BaseDirectory` / `Assembly.GetExecutingAssembly().Location`
- PowerShell：`$PSScriptRoot`（回退 `Get-Location`）
- Python：`os.path.dirname(os.path.abspath(__file__))`

新增入口必须沿用这条约定。`.bat` 启动器统一先 `cd /d "%~dp0"`。

### 文件即日志

不引入日志框架，每个工具有固定日志文件，编码 UTF-8：

| 文件 | 产出者 |
| --- | --- |
| `运行日志.txt` | `徽章抠图.exe --batch` |
| `排版日志.txt` | `排版工具.exe` |
| `_layout_log.txt` | `layout.ps1`（含逐槽位明细，比 exe 日志更啰嗦） |

日志同时是**验证证据**：里面记录每张图的输出尺寸、圆心、半径、页数与槽位映射。

### 内存内位图处理

图像算法一律用 `LockBits` + `Marshal.Copy` 直接操作字节缓冲（C#）
或 numpy 数组（Python），不用 `GetPixel`/`SetPixel`，因为要处理 2480×3508 量级的画布。

### 中文优先

面向操作者的提示语、日志、注释、文档全部用中文。`.bat` 文件保存为 GBK/ANSI 编码，
并在开头 `chcp 65001`；`.cs` / `.ps1` / `.py` / `.md` / `.txt` 保存为 UTF-8。

### 输出覆盖同名文件

各阶段输出同名 `.png` 并直接覆盖，不做备份、不加时间戳。`已排版\` 例外：每次运行先清空旧 PNG。

## Architecture Patterns

### 算法内核 + 双前端

同一个算法存在两份实现，必须保持功能等价：

| 能力 | exe 前端（主） | 脚本前端（辅助） |
| --- | --- | --- |
| 抠图 | `抠图工具.cs` → `徽章抠图.exe` | `cut_badge.ps1` |
| 排版 | `排版工具.cs` → `排版工具.exe` | `layout.ps1` |

改动算法时两边都要改，否则「双击 exe」和「双击 bat」的结果会分叉。

### 参数集中在入口

可调参数只在文件头的 `param(...)`（PowerShell）或 `argparse`（Python）里声明一次，
不散落在算法体内。GUI 只暴露最常调的参数（扫描阈值、羽化宽度），其余用源码常量。

### 确定性 vs 生成式

去水印有三条路线，**默认走确定性路线**，AI 路线是可选升级项：

- 确定性：`detex.py`（细纹压制）、`remove_watermark.py`（点阵层精确扣除）— 可复现、只改像素、保留透明通道；
- 生成式：`remove_watermark_ai.py`（本地 ComfyUI 重绘）、`豆包流程.bat`（在线 AI）— 观感更自然，但结果不可复现、会改动整体画面。

### 稳健拟合优于精确阈值

圆形定位统一采用「扫描/连通域拿到候选点 → RANSAC 剔除干扰点 → 最小二乘精修」，
而不是单一阈值分割，目的是抵抗边框条、云纹、飘带等干扰。

## Domain Context

- **徽章**：圆形金属徽章（珐琅/蚀刻）。实拍照片背景杂乱，圆形之外可能还有飘带、边框、角落图案。
- **待去除的水印**：约 13px 的淡色小字/点，按约 27px 的方格**斜向平铺**整张图，亮度只比周围高几个色阶，肉眼几乎看不清。
- **模板**：`排版demo.png`，A4 300dpi 竖版 2480×3508 白底图，上面印有圆形徽章槽位图案（当前 11 个）。
  换版面 = 换这张图，`每页张数` 由模板上的圆的个数决定。

## Important Constraints

- **仅 Windows**：依赖 .NET Framework 4.x 与 `System.Drawing`，`shlwapi.dll` 的自然排序（`StrCmpLogicalW`）也是 Windows 专属。
- **圆内必须完整不透明**：圆形区域内的白色文字、浅色纹样都要保留，不能出现空洞或半透明。
- **只支持完整圆形徽章**：非圆形徽章不适用。
- **输出尺寸与模板一致**：排版页必须等于模板尺寸（2480×3508，白底）。
- **透明通道必须保留**：去水印各路线只允许改 RGB/亮度，`alpha` 原样透传。
- **无联网依赖**（可选路线除外）：唯一的外部服务是本地 ComfyUI（`127.0.0.1:8188`）。
- **不使用破坏性快捷键操作**：处理是批量覆盖写的，运行前应确认输出目录内容可弃。

## External Dependencies

| 依赖 | 用途 | 缺失时的行为 |
| --- | --- | --- |
| .NET Framework 4.x | 两个 exe | Win10/11 内置；Win7 需自行安装 |
| `csc.exe`（`%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\`） | 从 `.cs` 重新编译 exe | 无法重建 exe，只能用已编译产物或 `.ps1` |
| Python 3.11 + numpy + Pillow | 三个去水印脚本 | 去水印不可用；抠图/排版不受影响 |
| ComfyUI + `v1-5-pruned-emaonly.safetensors` | `remove_watermark_ai.py` | AI 重绘不可用，回退到确定性去水印 |
| Python 解释器路径 `C:\Users\leafr\ComfyUI\.venv\Scripts\python.exe` | `去水印.bat` 硬编码 | 见 `openspec/specs/pipeline-orchestration/spec.md` 的已知偏差 |

## 编译 / 运行命令

```powershell
# 重新编译两个 exe（工作目录 = 项目根）
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /optimize+ `
  /out:徽章抠图.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll 抠图工具.cs

C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:exe /optimize+ `
  /out:排版工具.exe /r:System.Drawing.dll 排版工具.cs
```

```powershell
# 抠图（脚本版）
powershell -ExecutionPolicy Bypass -File cut_badge.ps1 -ScanT 45 -Feather 4 -Debug

# 去水印（确定性）
python detex.py --src 底图 --strength 中 --preview
python remove_watermark.py --src 底图 --dst 无水印 --pitch 27 --preview

# 去水印（AI 重绘，需 ComfyUI 在跑）
python remove_watermark_ai.py --denoise 0.65 --size 512

# 排版（脚本版）
powershell -ExecutionPolicy Bypass -File layout.ps1
```
