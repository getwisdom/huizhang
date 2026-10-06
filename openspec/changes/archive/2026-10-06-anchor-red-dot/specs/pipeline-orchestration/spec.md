# Spec Delta —— pipeline-orchestration（定位点样式 CLI 开关）

## Purpose

`koutu layout` 除 `--anchors / --no-anchors` 外，新增定位点样式开关 `--anchor-style {triangle,dot}`，与 GUI 下拉同一内核行为。

## MODIFIED Requirements

### Requirement: 排版定位点 CLI 开关
`koutu layout` SHALL 提供 `--anchors / --no-anchors`（控制是否在输出页绘制定位点，默认开启）与 `--anchor-style {triangle,dot}`（定位点样式：`triangle` = 黑三角（默认）、`dot` = 红点），语义与 GUI「添加定位点」勾选框及「样式」下拉一致（同一默认值、同一内核行为）；`--help` 中的说明 SHALL 为中文；非法的样式取值 SHALL 由 argparse 以退出码 2 拒绝且不生成任何页面。

#### Scenario: 默认开启
- **WHEN** 执行 `koutu layout`（不带开关）
- **THEN** 输出页包含黑三角定位点，排版日志标注定位点已开启与样式「黑三角」

#### Scenario: --no-anchors 关闭
- **WHEN** 执行 `koutu layout --no-anchors`
- **THEN** 输出页与既有基线一致、无定位点，排版日志标注定位点已关闭

#### Scenario: --anchor-style dot
- **WHEN** 执行 `koutu layout --anchor-style dot`
- **THEN** 输出页为红点定位点，排版日志标注样式「红点」

#### Scenario: 非法样式取值
- **WHEN** 执行 `koutu layout --anchor-style 圆点`
- **THEN** argparse 报错并以退出码 2 结束，不生成任何页面
