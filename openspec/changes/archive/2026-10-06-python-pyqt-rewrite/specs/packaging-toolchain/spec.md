# Spec Delta —— packaging-toolchain（交付与工具链）

## Purpose

让重写版以「绿色包」形态交付：不装 Python 也能双击运行、拷贝即用；同时固化开发侧环境、测试装置、编码约定与旧实现归档规则，保证交付物可复验。

## ADDED Requirements

### Requirement: Python 环境与依赖锁定
项目 SHALL 使用仓库内虚拟环境 `.venv`（Python 3.12.10）运行与构建；直接依赖（PyQt6 / numpy / Pillow / pytest / pyinstaller）SHALL 以精确版本锁定在根目录 `requirements.txt`；恢复命令与镜像参数 SHALL 写入文档（本机国际源很慢，用华为云镜像）。

#### Scenario: 重建环境
- **WHEN** 在新机器执行 `pip install -r requirements.txt`
- **THEN** `.venv` 内依赖与 `requirements.txt` 完全一致，pytest / PyInstaller 可用

### Requirement: PyInstaller 单目录绿色包
交付 SHALL 用 PyInstaller `--onedir --windowed` 构建单目录包（默认名 `koutu`）：主程序 `koutu.exe` 与 `_internal/` 必须整包分发；可替换资源 `排版demo.png` SHALL 位于 exe 同级目录（不埋进包内）；构建命令、产物规模与实测数据参照 `docs/环境验证.md` §5–6。

#### Scenario: 构建成功
- **WHEN** 执行打包命令（环境验证 §5 模板）
- **THEN** 退出码 0，`dist\koutu\` 内 exe 与 `_internal/` 齐备（规模与 §5.2 实测同一量级），构建警告无实质缺失

#### Scenario: 中文与空格路径双击
- **WHEN** 把整包复制到含中文与空格的路径并双击
- **THEN** 正常启动、写日志、退出码 0（参照 §6 实测）

### Requirement: 绿色包运行契约
打包产物 SHALL 不依赖系统 Python 与任何外部运行时；首次运行 SHALL 自动创建数据目录；SHALL NOT 触发 UAC 提权。未签名 exe 在启用防护的机器上可能触发 SmartScreen 提示，SHALL 在文档中说明处理方式（「更多信息 → 仍要运行」）。

#### Scenario: 模拟无 Python 机器
- **WHEN** 在未安装 Python 的机器（或清理 PATH 的会话）运行交付包
- **THEN** 两条主流程（GUI、CLI 批处理）都能完成并过阶段 1 / 2 判据

### Requirement: CLI 在打包版的行为
打包版采用无控制台（`--windowed`）构建；其 CLI 批处理的验收证据 SHALL 以「日志文件 + 退出码」为准（与旧 winexe 行为一致）；源码版（`.venv` 解释器）SHALL 支持控制台输出。

#### Scenario: 打包版批处理取证
- **WHEN** 在打包版执行 `koutu.exe cutout`
- **THEN** 生成 `运行日志.txt`，退出码符合契约，可据此判收

### Requirement: pytest 自动化测试装置
仓库 SHALL 以 `tests/`（pytest）承载自动化回归：冒烟用例验证装置与 golden 就位；每个重写模块的对照测试 SHALL 挂接 `golden/`（容差为各能力规格所述）；运行命令 SHALL 为 `.venv\Scripts\python.exe -m pytest tests -q`。测试 SHALL NOT 改动生产数据目录与 `golden/` 冻结物（在临时目录或副本中工作）。

#### Scenario: 装置自检
- **WHEN** 执行 `pytest tests -q`
- **THEN** 全部通过（基线：3 passed），且未改动任何生产目录

### Requirement: 编码与脚本约定
`.ps1` 脚本（含中文）SHALL 保存为 UTF-8 带 BOM；`.py / .md / .txt` SHALL 为 UTF-8；若保留 `.bat` 启动器 SHALL 用系统 ANSI（GBK）并 `chcp 65001`、设置 `PYTHONUTF8=1`；PowerShell 5.1 读 UTF-8 文本 SHALL 显式 `-Encoding UTF8`。新写的 `.ps1` SHALL 用 BOM 补写命令过一遍再提交。

#### Scenario: 新脚本可被执行策略正常加载
- **WHEN** 新增一个含中文的 `.ps1` 并直接运行
- **THEN** 不出现 GBK 误读导致的语法错误

### Requirement: legacy 归档与根目录整洁
旧实现文件（`抠图工具.cs / 排版工具.cs / cut_badge.ps1 / layout.ps1 / detex.py / remove_watermark.py / remove_watermark_ai.py / ocr.ps1 / scan_watermark.ps1 / _analyze.ps1 / _probe_demo.ps1 / 各 .bat`）SHALL 整体归档到根目录 `legacy/`（只归档、不删除），并附 `legacy/README.md` 说明历史状态与「不参与验收」。归档后仓库根 SHALL NOT 再保留旧入口与旧实现；`golden/tools/` 的冻结副本 SHALL NOT 被动。git 提交前 SHALL 检查 `git status`，确认没有把数据目录 / `.venv` / 运行日志带入库。

#### Scenario: 归档后盘点
- **WHEN** 归档完成后执行 `git status` 与目录盘点
- **THEN** 根目录只剩新程序、文档、规格与装置；`legacy/` 完整包含旧实现；数据目录零改动
