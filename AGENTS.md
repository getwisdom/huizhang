# AGENTS.md

本仓库使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 做规格驱动开发（CLI 已安装，schema = `spec-driven`）。

| 位置 | 含义 |
| --- | --- |
| `openspec/specs/` | **当前已经做到的行为**（基线规格，改代码后必须同步） |
| `openspec/changes/` | **准备改什么**（提案 + 规格差异 + 任务） |
| `openspec/config.yaml` | 项目上下文与产物规则（**机器读的就是这里**） |
| `PROJECT.md`（项目根） | 给人看的完整项目说明：技术栈、目录契约、领域背景、编译命令 |
| `.agents/skills/openspec-*` | OpenSpec 工作流技能（全 12 个，见文末「工作流集合」） |

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 用之前先自检 | `openspec doctor` |
| 列出规格 / 提案 | `openspec list --specs` / `openspec list` |
| 读某个规格 | `openspec show <capability>` |
| 校验全部规格 | `openspec validate --strict --all` |
| 新建提案 | `openspec new change "<change-id>"` |
| 看提案进度 | `openspec status --change "<change-id>"` |
| 取某个产物的写法与模板 | `openspec instructions <proposal|specs|design|tasks> --change "<change-id>"` |
| 归档提案 | `openspec archive <change-id>` |

> 本机 PowerShell 已可直接敲 `openspec`，无需 `.cmd` 后缀（见文末「已知环境问题」）。

## 工作流

产物顺序为 **proposal → specs → design → tasks**。

1. **先读规格**：动任何脚本前，先读 `openspec/config.yaml` 的 `context`、项目根的 `PROJECT.md`
   和 `openspec/specs/` 下相关的能力规格。
2. **改动前先建提案**：`openspec new change "<change-id>"`。提案要写清：为什么改、改什么、影响哪条路线、
   是否需要同步双实现，以及非目标（不做什么）。跨脚本、跨路线或改算法参数时才补 `design.md`。
3. **写规格差异**：放在 `openspec/changes/<change-id>/specs/<capability>/spec.md`，
   用 `## ADDED / MODIFIED / REMOVED Requirements` 分段，每条按 `### Requirement:` + `#### Scenario:` 写，
   **每个 Requirement 至少一个 Scenario**（`--strict` 会强制检查）。
4. **实现**：按 `tasks.md` 逐条完成，完成后把对应项标成 `[x]`。
5. **归档**：`openspec archive <change-id>`，它会校验并把差异合并进 `openspec/specs/`。

改动未走提案也可以，但**必须先更新 `openspec/specs/`**，且 `openspec validate --strict --all` 必须全绿。

## 本仓库的硬约束

- **双实现同步**：抠图算法同时存在于 `抠图工具.cs`（编译成 `徽章抠图.exe`）和 `cut_badge.ps1`
  （`Add-Type` 内联 C#）；排版算法同时存在于 `排版工具.cs`（`排版工具.exe`）和 `layout.ps1`。
  改一侧必须同步另一侧，否则两个入口行为会分叉。
- **不要改目录契约**：`原图 / 底图 / 无水印 / 无水印_细纹轻 / 无水印_细纹重 / 无水印底图 / 已排版 / doubao`
  这些中文目录名是脚本之间、也是给操作者的接口，改名会同时打断 `使用说明.txt`、`排版工具使用说明.txt`、
  `豆包流程.bat` 与各 `.bat` 入口。
- **一切以脚本/exe 所在目录为根**：用 `$PSScriptRoot` / `os.path.dirname(os.path.abspath(__file__))` /
  `AppDomain.CurrentDomain.BaseDirectory`，不要写死绝对路径——整个目录必须能拷到别的电脑直接跑。
- **Windows-only**：依赖 .NET Framework 4.x、`System.Drawing`、`System.Windows.Forms`、WinRT OCR。
  不要为了"跨平台"抽一层——那会破坏"双击即用"这个核心承诺。
- **不引入包管理**：exe 用系统自带 `csc.exe` 现场编译；Python 脚本只依赖 `numpy` + `Pillow`
  （AI 路线额外依赖本地 ComfyUI，且必须可降级而不影响其它路线）。
- **文件编码**：`.cs` / `.ps1` / `.py` / `.md` / `.txt` 一律 UTF-8；`.bat` 用系统 ANSI（GBK）
  并在开头 `chcp 65001`，配合 `set PYTHONUTF8=1` 避免 Python 输出乱码。
- **面向操作者一律中文**：界面文案、日志、文档、错误提示都用中文。
- **日志是验收证据**：改处理逻辑时保留 `运行日志.txt` / `排版日志.txt` / `_layout_log.txt` 里的统计行
  （不透明像素数、检测到的圆心半径、槽位分配表、水印幅度降幅），它们是人工核对正确性的唯一手段。

## 验证方式

本仓库没有自动化测试、没有构建系统、也不是 git 仓库。改动后请按这个顺序自证：

1. `openspec validate --strict --all` 必须全部通过；
2. 跑一遍受影响的脚本或 `.bat`，对照能力规格里的 Scenario 检查日志统计行；
3. 需要像素级证据时用辅助脚本：`_analyze.ps1`（底图与原图差值）、`_probe_demo.ps1`（模板结构探测）、
   `scan_watermark.ps1`（水印扫描）、`ocr.ps1`（读图上的文字及位置框）；
4. 影响操作者用法的改动，同步更新 `总结文档.md`、`使用说明.txt`、`排版工具使用说明.txt`；
5. 在最终回复里说明：跑了什么、看到什么数字、哪些没验证。

## 已知环境问题

- **PowerShell 执行策略（本机已处理）**：本机已设 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，
  所以 PowerShell 里能直接敲 `openspec`、`npm`。根因是 npm 会同时生成 `openspec.ps1` 与 `openspec.cmd`，
  PowerShell 优先解析 `.ps1`（`PATHEXT` 里根本没有 `.PS1`，是 PowerShell 特殊优先匹配），
  撞上执行策略就报「无法加载文件 openspec.ps1」。换到执行策略仍为 Restricted 的机器时，
  改用 `openspec.cmd`，或同样设一次 RemoteSigned。
- OpenSpec CLI 默认收集匿名使用统计；关闭方式：`openspec config set telemetry.enabled false`。
- **`PROJECT.md` 放在项目根，不在 `openspec/`**：OpenSpec 1.x 不再把 `openspec/project.md` 当作项目上下文
  （改由 `openspec/config.yaml` 的 `context` 承载），留在 `openspec/` 里会被 `init` 反复提示清理。
  文档本身对人有用，所以搬到了项目根；项目约定变更时两份都要改。
- **工作流技能装在 `.agents/skills/`**（`--tools agents`，厂商中立）。重装/更新用：
  `openspec init --tools agents --no-animation`——实测不会覆盖 `openspec/config.yaml`，可以放心重跑。
  技能集合跟随全局 profile：改完 profile 后必须再跑一次 init，`.agents/skills/` 才会刷新。

## 工作流集合

本机全局配置（`%APPDATA%\openspec\config.json`）为 `profile: custom`，启用全部 **12** 个工作流：

| 工作流 | 技能目录 | 用途 |
| --- | --- | --- |
| propose | `openspec-propose` | 一次生成完整提案（proposal + specs + design + tasks） |
| explore | `openspec-explore` | 立项前的思考伙伴，只思考、不写代码 |
| new | `openspec-new-change` | 分步新建变更，逐个产物推进、每步可确认 |
| continue | `openspec-continue-change` | 接着创建下一个尚未生成的产物 |
| apply | `openspec-apply-change` | 按 tasks.md 逐条实现；也可中途续做 |
| update | `openspec-update-change` | 修订已有产物并保持彼此一致 |
| ff | `openspec-ff-change` | 快进：一口气创建实现所需的全部产物，不逐步确认 |
| sync | `openspec-sync-specs` | 把 delta 规格合并进主规格（不归档） |
| archive | `openspec-archive-change` | 归档单个变更并更新主规格 |
| bulk-archive | `openspec-bulk-archive-change` | 一次归档多个变更 |
| verify | `openspec-verify-change` | 归档前校验实现与变更产物是否一致 |
| onboard | `openspec-onboard` | 带讲解地跑一遍完整工作流，作入门导览 |

回到精简的 6 个工作流：`openspec config profile core`，再在本目录跑一次 `openspec init --tools agents`。
配置文件是 JSON，`workflows` 是数组——`openspec config set` **不支持**数组（会报 `expected array, received string`），
需要用预设 `core` 或直接改 JSON。
