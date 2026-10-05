# pipeline-orchestration Specification

## Purpose

定义各处理阶段之间的**目录契约**、一键流程入口与日志约定。

这是本仓库最重要的稳定性边界：中文目录名既是脚本之间的接口，也是写给操作者的文件名接口，
改名会同时打断脚本、`.bat` 入口和使用说明文档。

## Stage Directory Contract

| 阶段 | 输入目录 | 输出目录 | 工具 |
| --- | --- | --- | --- |
| 抠图 | `原图` | `底图` | `徽章抠图.exe` / `cut_badge.ps1` |
| 去水印（细纹·中档） | `底图` | `无水印` | `detex.py --strength 中` |
| 去水印（细纹·轻/重） | `底图` | `无水印_细纹轻` / `无水印_细纹重` | `detex.py --strength 轻/重` |
| 去水印（点阵精确） | `底图` | `无水印` | `remove_watermark.py` |
| 去水印（AI 重绘） | `底图` | `无水印` | `remove_watermark_ai.py` |
| 在线去水印后抠图 | `doubao` | `无水印底图` | `豆包流程.bat` → `cut_badge.ps1` |
| 排版 | `底图` + `排版demo.png` | `已排版` | `排版工具.exe` / `layout.ps1` |

不在契约内的目录（`无水印_精修`、`无水印_AI重绘`、`水印诊断`，以及 `去水印_预览` 中的历史文件）
由人工操作或早期实验产生，SHALL NOT 被当成流程的一环。

---

## Requirements

### Requirement: 目录契约稳定

系统 SHALL 用固定中文目录名承载阶段之间与操作者之间的接口，且这些名字 SHALL NOT 被重命名或改为可配置。

- 阶段读写目录见上表；每个阶段的输出目录 SHALL 是下一个阶段的输入目录。
- 输出文件名 SHALL 为输入文件主名 + `.png`，便于操作者按文件名核对上一阶段的产物。
- 目录不存在时，产出该目录的工具 SHALL 自动创建它，而不是报错要求手工建目录。

#### Scenario: 换批次不影响目录契约
- **WHEN** 操作者把「底图」内容全部替换成另一批徽章
- **THEN** 直接双击「排版.bat」即可重新排版，无需改任何脚本

### Requirement: 一键流程入口

系统 SHALL 为每条常用路径提供双击即用的 `.bat` 入口。

- 每个 `.bat` SHALL 先 `cd /d "%~dp0"` 切到自身所在目录，使相对路径与 exe 的"程序所在目录"语义一致。
- `.bat` SHALL 以 `chcp 65001` 打开 UTF-8 代码页，避免中文提示与 Python 输出乱码。
- 涉及 Python 的入口 SHALL 设置 `PYTHONUTF8=1` 或 `PYTHONIOENCODING=utf-8`。
- 每个 `.bat` 结束时 SHALL `pause`，保证操作者能看到结果。

#### Scenario: 抠图入口
- **WHEN** 双击「抠图.bat」
- **THEN** 以 `-ExecutionPolicy Bypass` 调起 `cut_badge.ps1`，处理「原图」→「底图」

### Requirement: 豆包在线去水印衔接流程

系统 SHALL 提供在线 AI 去水印与本地抠图衔接的一键流程，因为在线 AI 无法由脚本直接驱动。

- 流程 SHALL 明确三步：用豆包处理「原图」里的图片 → 把导出图片放进「doubao」文件夹 → 双击「豆包流程.bat」。
- 该脚本 SHALL 执行 `cut_badge.ps1 -InputDir "doubao" -OutputDir "无水印底图"`。
- 脚本内的提示文字 SHALL 说明输出位置是「无水印底图」。

#### Scenario: 豆包流程输出
- **WHEN** 「doubao」目录放好在线去水印后的照片并双击「豆包流程.bat」
- **THEN** 「无水印底图」得到透明背景 PNG

### Requirement: 脚本根目录定位

所有脚本与 exe SHALL 以自身所在目录作为工作根目录，不得依赖当前工作目录，也不得写死绝对路径。

- PowerShell SHALL 用 `$PSScriptRoot`（为空时回退到当前目录）。
- Python SHALL 用 `os.path.dirname(os.path.abspath(__file__))`。
- C# SHALL 用 `AppDomain.CurrentDomain.BaseDirectory` 或程序集所在位置。
- 输入/输出参数为相对路径时 SHALL 相对于该根目录解析；为绝对路径时 SHALL 直接使用。

#### Scenario: 整目录搬迁
- **WHEN** 把 `排版工具.exe`、`排版demo.png`、`底图\` 拷到另一台 Windows 电脑
- **THEN** 双击 exe 即可运行，无需任何安装或改配置

### Requirement: 运行日志

每个阶段 SHALL 把本次运行的记录写入固定文件名的日志，供事后核对。

- 抠图 exe：`运行日志.txt`；排版 exe：`排版日志.txt`；排版脚本：`_layout_log.txt`。
- 日志 SHALL 含：使用的输入目录、输出目录、关键参数、逐文件处理结果、以及汇总统计。
- 日志 SHALL 以 UTF-8 写出（exe 版本带 BOM，便于 Windows 记事本直接打开）。

#### Scenario: 事后追溯失败原因
- **WHEN** 某张图处理失败
- **THEN** 日志里该文件对应行以 `[失败]` 开头并附失败原因，汇总行给出成功/失败张数
