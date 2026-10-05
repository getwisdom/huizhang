# koutu · 徽章图片批处理工具集

Windows 单机、离线优先的徽章照片批处理工具集：把一批拍摄来的徽章照片，处理成可以直接付印的 A4 排版页。

```
原图\  ──抠图──▶  底图\  ──排版──▶  已排版\第N页.png
（去水印为入口占位：本版不实现算法，后续版本提供）
```

面向的使用者是不写代码的操作人员：把整个目录拷到任意 Windows 电脑，双击 `.exe` 或 `.bat` 就能跑，
不需要装 Python、PowerShell 模块或任何第三方运行时。

## 三段流程

| 阶段 | 做什么 | 主入口 | 输入 → 输出 |
| --- | --- | --- | --- |
| 抠图 | 识别照片中间的圆形徽章，裁成透明背景 PNG | `徽章抠图.exe` / `抠图.bat` | `原图\` → `底图\` |
| 去水印 | 入口占位——本版不实现算法（后续版本提供） | ——（旧 `去水印.bat` / `去水印AI.bat` 已归档 `legacy\`） | —— |
| 排版 | 按模板图上自动识别的圆形槽位排成多页 A4 PNG | `排版工具.exe` / `排版.bat` | `底图\` + `排版demo.png` → `已排版\` |

去水印：本版不实现算法（入口占位、后续版本提供）；旧路线脚本 `detex.py` / `remove_watermark.py` / `remove_watermark_ai.py`
已归档 `legacy\`，研究留档见 `docs/水印研究.md`。

## 先编译再运行

本仓库只跟踪源码，不跟踪编译产物。克隆后请先在项目根执行一次：

```powershell
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /optimize+ `
  /out:徽章抠图.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll 抠图工具.cs

C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:exe /optimize+ `
  /out:排版工具.exe /r:System.Drawing.dll 排版工具.cs
```

不想编译也可以直接用脚本版：`抠图.bat`、`排版.bat` 走的就是 `.ps1` 侧的实现。

## 目录即接口

各阶段用固定的中文目录名交互，这些名字同时是脚本之间的接口和给操作者的文件接口，**不可重命名**：

`原图\` · `底图\` · `无水印\` · `无水印_细纹轻\` · `无水印_细纹重\` · `无水印底图\` · `已排版\` · `doubao\`

目录由脚本自动创建，不需要手工建。完整契约见 [`openspec/specs/pipeline-orchestration/spec.md`](openspec/specs/pipeline-orchestration/spec.md)。

## 文档

| 文件 | 内容 |
| --- | --- |
| [`PROJECT.md`](PROJECT.md) | 技术栈、目录契约、架构模式、编译命令 |
| [`使用说明.txt`](使用说明.txt) | 抠图工具的操作步骤 |
| [`排版工具使用说明.txt`](排版工具使用说明.txt) | 排版工具的操作步骤 |
| [`总结文档.md`](总结文档.md) | 整体流程与算法说明 |
| [`AGENTS.md`](AGENTS.md) | 给 AI 协作者的仓库约定与 OpenSpec 工作流 |
| `openspec/specs/` | 各能力的基线规格（当前已做到的行为） |

## 主要约束

- **仅 Windows**：依赖 .NET Framework 4.x、`System.Drawing`、`System.Windows.Forms`，以及 WinRT OCR。
- **双实现同步**：抠图算法同时存在于 `抠图工具.cs` 和 `cut_badge.ps1`，排版算法同时存在于 `排版工具.cs` 和 `layout.ps1`，
  改一侧必须同步另一侧，否则两个入口行为会分叉。
- **一切以脚本/exe 所在目录为根**：不写死绝对路径，整个目录可搬迁。
- **保留透明通道**：抠图输出（含羽化带）与排版的 `alpha` 语义不可被破坏；去水印本版不处理像素（后续版本实现时沿用该约束）。
- **日志是验收证据**：`运行日志.txt` / `排版日志.txt` / `_layout_log.txt` 里的统计行是人工核对正确性的手段。
- **没有自动化测试和 CI**：改动后需实际运行受影响的脚本，并对照能力规格里的 Scenario 检查日志。
