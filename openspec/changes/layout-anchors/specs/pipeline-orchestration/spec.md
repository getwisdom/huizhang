# Spec Delta —— pipeline-orchestration（排版定位点 CLI 开关）

## ADDED Requirements

### Requirement: 排版定位点 CLI 开关
`koutu layout` SHALL 提供 `--anchors / --no-anchors` 开关，控制是否在输出页绘制定位点；默认开启，语义与 GUI「添加定位点」勾选框一致（同一默认值、同一内核行为）；`--help` 中的该开关说明 SHALL 为中文。

#### Scenario: 默认开启
- **WHEN** 执行 `koutu layout`（不带开关）
- **THEN** 输出页包含定位点，排版日志标注定位点已开启

#### Scenario: --no-anchors 关闭
- **WHEN** 执行 `koutu layout --no-anchors`
- **THEN** 输出页与既有基线一致、无定位点，排版日志标注定位点已关闭
