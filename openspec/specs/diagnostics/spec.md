# diagnostics Specification

## Purpose

本能力定义**验收装置与排查约定**，不参与生产流程：`golden/scripts/`（哈希清单 / 清单比对 / 像素对照）
是长期验收装置；旧探针脚本（`ocr.ps1 / scan_watermark.ps1 / _analyze.ps1 / _probe_demo.ps1`）
归档 `legacy/` 后仅作只读排查工具。

装置与排查脚本只约束**观测口径**（读什么、输出什么量纲），不约束其存续；任何排查不得修改生产目录。

## Requirements

### Requirement: 金标准哈希清单脚本口径
`golden/scripts/hash-tree.ps1` SHALL 生成目录内容的 SHA256 清单 CSV，列为 `RelPath, Length, LastWriteTimeUtc, SHA256`，按 `RelPath` 排序；`-Include` SHALL 接受逗号字符串与数组两种写法；目标不存在时 SHALL 写入 `<MISSING>` 行而不是静默跳过。

#### Scenario: 原仓库零改动复核
- **WHEN** 对 13 个数据目录（66 个文件）生成清单并与冻结清单比对
- **THEN** 输出「差异数: 0」（退出码 0）

#### Scenario: 旧工具身份复核
- **WHEN** 对旧工具脚本集合生成清单并与 `golden/checksums/tools_binaries.csv` 比对
- **THEN** 差异数 0（作为重写期间「旧工具未被改动」的证据）

### Requirement: 清单比对与像素对照脚本口径
`compare-manifests.ps1` SHALL 比对两份清单并区分三类差异（仅 Before / 仅 After / 内容不同），完全一致退出码 0，否则 1。`pixel-diff.ps1` SHALL 对同尺寸两张 PNG 输出：尺寸、`opaqueA / opaqueB`、alpha 差>8 的像素数与占比、最大 alpha 差、双方可见像素 RGB 差>8 的像素数与占比；尺寸不同时 SHALL 输出 `SIZE_DIFF`。

#### Scenario: 阶段 1 / 阶段 2 对照
- **WHEN** 用验收清单命令对照基线（抠图 7 张、排版 1 页）
- **THEN** 输出上述字段，作为通过/失败判定依据

### Requirement: 排查工具与产物规范
`golden/scripts/` SHALL 作为长期验收装置保留。旧探针脚本（`ocr.ps1 / scan_watermark.ps1 / _analyze.ps1 / _probe_demo.ps1`）归档 `legacy/` 后仅作只读排查工具，不属于产品入口。新的排查产物 SHALL 使用 `_probe_*` / `诊断_*` 前缀，与生产目录产物明确区分；排查 SHALL NOT 修改或删除任何生产目录里的文件；新增排查脚本 SHALL 在文件头注释里写明用途与可删除性。

#### Scenario: 探测不污染生产目录
- **WHEN** 用排查工具分析模板或底图
- **THEN** 新增文件只有 `_probe_*` / `诊断_*` 类产物，「原图」「底图」「已排版」里的文件一个都没被改动
