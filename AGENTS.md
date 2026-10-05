# AGENTS.md

本仓库使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 做规格驱动开发（CLI 已安装，schema = `spec-driven`）。
仓库正在按提案 **`python-pyqt-rewrite`** 重写为 **Python + PyQt6 单程序**（页签：抠图 / 排版 / 去水印占位——本版不实现去水印算法，仅保留入口占位、算法后续版本提供）；实施按 `openspec/changes/python-pyqt-rewrite/tasks.md` 的 W0–W6 波次推进。

| 位置 | 含义 |
| --- | --- |
| `openspec/specs/` | **当前已经做到的行为**（基线规格；本变更归档后切换为新世界） |
| `openspec/changes/` | **准备改什么**（提案 + 规格差异 + 任务） |
| `openspec/config.yaml` | 项目上下文与产物规则（**机器读的就是这里**） |
| `PROJECT.md`（项目根） | 给人看的完整项目说明 |
| `docs/验收清单.md` | 验收判据与容差（唯一数值来源；对照 `golden/`） |
| `golden/` | 旧工具行为的冻结基线（只读；对照命令在 `golden/scripts/`） |
| `legacy/` | 旧实现归档（只归档不删除；只读参考、不参与验收） |
| `.agents/skills/openspec-*` | OpenSpec 工作流技能 |

## 常用命令

| 目的 | 命令 |
| --- | --- |
| 用之前先自检 | `openspec doctor` |
| 列出规格 / 提案 | `openspec list --specs` / `openspec list` |
| 读某个规格 | `openspec show <capability>` |
| 校验全部规格 | `openspec validate --strict --all` |
| 新建提案 | `openspec new change "<change-id>"` |
| 看提案进度 | `openspec status --change "<change-id>"` |
| 取某个产物的写法与模板 | `openspec instructions <proposal\|specs\|design\|tasks> --change "<change-id>"` |
| 归档提案 | `openspec archive <change-id>` |
| 跑测试 | `.venv\Scripts\python.exe -m pytest tests -q` |
| 打包（W5 起） | `packaging\打包.ps1`；命令模板见 `docs/环境验证.md` §5 |

> 本机 PowerShell 已可直接敲 `openspec`，无需 `.cmd` 后缀（见文末「已知环境问题」）。

## 工作流

产物顺序为 **proposal → specs → design → tasks**。

1. **先读规格**：动任何代码前，先读 `openspec/config.yaml` 的 `context`、项目根的 `PROJECT.md` 和 `openspec/specs/` 下相关的能力规格；对照物与容差看 `docs/验收清单.md`。
2. **改动前先建提案**：`openspec new change "<change-id>"`。提案要写清：为什么改、改什么、影响哪条路线（抠图 / 排版 / 流程契约）、是否需要挂 golden 对照或补 pytest 用例，以及非目标（不做什么）。跨模块或调整算法参数时才补 `design.md`。
3. **写规格差异**：放在 `openspec/changes/<change-id>/specs/<capability>/spec.md`，用 `## ADDED / MODIFIED / REMOVED Requirements` 分段，每条按 `### Requirement:` + `#### Scenario:` 写，**每个 Requirement 至少一个 Scenario**（`--strict` 会强制检查）。
4. **实现**：按 `tasks.md` 逐条完成，完成后把对应项标成 `[x]`。
5. **归档**：`openspec archive <change-id>`，它会校验并把差异合并进 `openspec/specs/`。

改动未走提案也可以，但**必须先更新 `openspec/specs/`**，且 `openspec validate --strict --all` 必须全绿。

## 本仓库的硬约束

- **单实现 + 金标准回归**：正式实现只有 `koutu/`（Python）一份；旧实现（C# / PowerShell / 旧 Python）整体归档 `legacy/`，只读参考、不再演进、不参与验收。行为改动以 `golden/` 对照 + `docs/验收清单.md` 容差为准（**禁止对旧产物做逐字节 SHA 对照**，一律走像素级指标 + 日志统计行）。
- **不要改目录契约**：`原图 / 原图_去水印 / doubao / 底图 / 无水印 / 无水印_AI重绘 / 无水印_精修 / 无水印_细纹轻 / 无水印_细纹重 / 无水印底图 / 去水印_预览 / 已排版 / 水印诊断` 这些中文目录名是给操作者的接口，**不可重命名、不可删除**；新程序的自动流程只读写 `原图 → 底图 → 已排版`。
- **一切以程序根为根**：打包版 = `koutu.exe` 所在目录（`os.path.dirname(os.path.abspath(sys.executable))`）；源码版 = 仓库根。不依赖当前工作目录，不写死绝对路径。
- **Windows-only**：依赖 Python 3.12 + PyQt6 / numpy / Pillow；交付为 PyInstaller `--onedir --windowed` 单目录绿色包（不装 Python 也能双击跑）。不做跨平台适配。
- **依赖与构建**：解释器用仓库 `.venv`（`D:\workspace\koutu\.venv\Scripts\python.exe`；裸 `python` 是商店占位符，别用）；依赖精确锁定在 `requirements.txt`；装包用华为云镜像（`-i https://mirrors.huaweicloud.com/repository/pypi/simple`）。
- **不引入联网服务**：运行期不得依赖网络或外部服务（AI 去水印为非目标）。
- **文件编码**：`.py / .md / .txt` 一律 UTF-8；`.ps1` 一律 UTF-8 **带 BOM**（PowerShell 5.1 会按 GBK 误读导致语法错）；如保留 `.bat` 用系统 ANSI（GBK）并在开头 `chcp 65001`。
- **面向操作者一律中文**：界面文案、日志、文档、错误提示都用中文。
- **日志是验收证据**：`运行日志.txt`（抠图）/ `排版日志.txt`（排版，含槽位分配表）里的统计行是人工核对正确性的唯一手段，改处理逻辑必须保留统计行语义。

## 验证方式

改动后请按这个顺序自证：

1. `openspec validate --strict --all` 必须全部通过；
2. `.venv\Scripts\python.exe -m pytest tests -q` 全绿（对照用例挂接 `golden/`）；
3. 实跑受影响的入口（GUI 或 CLI 子命令），贴出日志统计行作为证据；试验一律在独立「运行目录」或副本里做，**禁止在仓库根直接跑会写盘的工具**；
4. 需要像素级证据时用 `golden/scripts/`（hash-tree / compare-manifests / pixel-diff / run_step）与 `docs/验收清单.md` 的阶段判据；
5. 在最终回复里说明：跑了什么、看到什么数字、哪些没验证。

## 已知环境问题

- **PowerShell 执行策略（本机已处理）**：本机已设 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`，所以 PowerShell 里能直接敲 `openspec`、`npm`。根因是 npm 会同时生成 `openspec.ps1` 与 `openspec.cmd`，PowerShell 优先解析 `.ps1`（`PATHEXT` 里根本没有 `.PS1`，是 PowerShell 特殊优先匹配），撞上执行策略就报「无法加载文件 openspec.ps1」。换到执行策略仍为 Restricted 的机器时，改用 `openspec.cmd`，或同样设一次 RemoteSigned。
- **PowerShell 5.1 编码三连坑**：含中文的 `.ps1` 必须存成 UTF-8 **带 BOM**（否则按 GBK 误读、语法报错）；`Get-Content` 读 UTF-8 文本要加 `-Encoding UTF8`；用工具（编辑器/AI）写出的文件默认无 BOM，写 `.ps1` 后要过一遍补 BOM 命令（见 `docs/环境验证.md` §7）。
- **OpenSpec CLI 默认收集匿名使用统计**；关闭方式：`openspec config set telemetry.enabled false`。
- **`PROJECT.md` 放在项目根，不在 `openspec/`**：OpenSpec 1.x 不再把 `openspec/project.md` 当作项目上下文（改由 `openspec/config.yaml` 的 `context` 承载），留在 `openspec/` 里会被 `init` 反复提示清理。文档本身对人有用，所以搬到了项目根；项目约定变更时两份都要改。
- **git**：新开的终端可直接用 `git`；旧会话（环境变量未刷新）用全路径 `C:\Program Files\Git\cmd\git.exe`。提交信息用中文；提交前先 `git status` 确认没有把数据目录 / `.venv` / 运行日志带进来。
- **工作流技能装在 `.agents/skills/`**（`--tools agents`，厂商中立）。重装/更新用：`openspec init --tools agents --no-animation`——实测不会覆盖 `openspec/config.yaml`，可以放心重跑。技能集合跟随全局 profile：改完 profile 后必须再跑一次 init，`.agents/skills/` 才会刷新。

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
