# koutu · 徽章图片处理（Python + PyQt6 单程序）

Windows 单机、离线优先的徽章照片批处理工具：把一批拍摄来的徽章照片，处理成可以直接付印的 A4 排版页。

```
原图\  ──抠图──▶  底图\  ──排版──▶  已排版\第N页.png
（去水印为入口占位：本版不实现算法，后续版本提供）
```

一个主窗口三个页签（抠图 / 排版 / 去水印占位）+ 一套 CLI 子命令；交付为 PyInstaller 单目录绿色包——
把交付目录拷到任意 Windows 电脑，双击 `koutu.exe` 就能跑，不需要装 Python 或任何运行时。

## 页签（能力）

| 页签 | 做什么 | 输入 → 输出 |
| --- | --- | --- |
| 抠图 | 识别照片中间的圆形徽章，裁成透明背景 PNG | `原图\` → `底图\` |
| 排版 | 按模板图上自动识别的圆形槽位排成多页 A4 PNG（槽位内侧的小三角「定位点」默认开启、可关） | `底图\` + `排版demo.png` → `已排版\` |
| 去水印 | 入口占位——本版不实现算法（后续版本提供），不执行任何处理 | —— |

## 快速开始

```powershell
# 源码运行（开发机，用仓库 .venv 解释器；参数默认值见 CLI --help）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu              # GUI（三页签）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu cutout       # CLI 抠图（原图 → 底图）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu layout       # CLI 排版（底图 → 已排版；--no-anchors 关闭定位点）
& D:\workspace\koutu\.venv\Scripts\python.exe -m koutu watermark    # CLI 去水印（占位；退出码 2）
& D:\workspace\koutu\.venv\Scripts\python.exe -m pytest tests -q    # 测试（挂接 golden）

# 打包（生成 dist\koutu\ = koutu.exe + _internal\ + 排版demo.png + 使用说明.txt）
powershell -ExecutionPolicy Bypass -File packaging\打包.ps1
```

`dist\`、`build\`、`*.exe` 不入库；交付时整目录（exe 与 `_internal\` 一起）拷贝分发。

## 目录即接口

自动流程**默认**只读写三个环节目录：`原图\` → `底图\` → `已排版\`（缺失时自动创建）。
操作者也可以在界面里显式改选输入/输出目录（浏览 / 手输 / 恢复默认，自动记忆；默认不动时行为不变）；
安全规则：仅默认「已排版」保留「写入前清空旧页」，自定义输出目录只写不删（日志提示计数）。
全部 13 个历史中文目录名（含 `无水印*`、`doubao`、`原图_去水印` 等）是不可重命名、不可删除的接口；
本版对 `无水印*` 系目录没有任何自动写入者。完整契约见 `openspec/specs/pipeline-orchestration/spec.md`。

## 硬约束（维护者须知）

- **单实现 + 金标准回归**：正式实现只有 `koutu/` 一份；行为对照 `golden/`（像素级指标 + 日志统计行，
  **禁止逐字节 SHA 对照**）；容差唯一来源 `docs/验收清单.md`。
- **一切以「程序根」为根**：打包版 = `koutu.exe` 所在目录；源码版 = 仓库根；不依赖当前工作目录。
- **日志是验收证据**：`运行日志.txt`（抠图）/ `排版日志.txt`（排版，含槽位分配表），固定写在程序根。
- **编码**：`.py / .md / .txt` = UTF-8；`.ps1` = UTF-8 **带 BOM**；界面文案与日志全中文。
- **Windows-only**；运行期不依赖网络或外部服务。

## 仓库地图

| 位置 | 内容 |
| --- | --- |
| `koutu/` | 正式实现（core / cli / gui） |
| `packaging/` | `koutu.spec` + `打包.ps1` |
| `tests/` | pytest 回归（挂接 golden） |
| `golden/` | 旧工具行为的冻结基线（只读；对照命令在 `golden/scripts/`） |
| `legacy/` | 旧实现归档（只读参考、不参与验收；旧文档在 `legacy/docs/`） |
| `docs/` | 验收清单、环境验证、各波汇报（`docs/汇报/`） |
| `openspec/` | 规格驱动产物（proposal / specs / changes） |
| `dist/`（构建产生，不入库） | 交付包 `dist\koutu\`（整目录分发） |

## 文档

| 文件 | 内容 |
| --- | --- |
| [`使用说明.txt`](使用说明.txt) | 操作者文档（随交付包分发）：三页签操作、CLI、日志位置、常见问题 |
| [`docs/验收清单.md`](docs/验收清单.md) | 验收判据与容差（唯一数值来源） |
| [`PROJECT.md`](PROJECT.md) | 给维护者的完整项目说明 |
| [`AGENTS.md`](AGENTS.md) | 仓库约定与 OpenSpec 工作流 |
