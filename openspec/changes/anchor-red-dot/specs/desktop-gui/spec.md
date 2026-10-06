# Spec Delta —— desktop-gui（定位点样式下拉与记忆）

## Purpose

「排版」页签的定位点参数面从「一个勾选框」扩展为「勾选框 + 样式下拉（黑三角 / 红点）」，两者都由 QSettings 记忆，并在任务运行期间禁用。

## MODIFIED Requirements

### Requirement: 排版定位点开关与样式（勾选框、下拉与记忆）
「排版」页签 SHALL 提供「添加定位点」勾选框（默认勾选）与其右侧「样式」下拉（选项「黑三角」/「红点」，默认「黑三角」）；样式下拉在校选框未勾选时与任务运行期间 SHALL 被禁用（不可修改），任务结束后恢复；勾选状态与样式 SHALL 随现有 QSettings 机制记忆（键 `layout/anchors`、`layout/anchor_style`；程序根 `koutu.ini`，不可写时回退 `%APPDATA%\koutu\koutu.ini`）并在重开程序时恢复；勾选与样式的语义 SHALL 与 CLI `--anchors / --no-anchors`、`--anchor-style` 一致。

#### Scenario: 默认勾选
- **WHEN** 全新环境首次启动程序
- **THEN** 「添加定位点」处于勾选状态，「样式」下拉为「黑三角」

#### Scenario: 记忆保持
- **WHEN** 操作者取消勾选后关闭程序并重新打开
- **THEN** 勾选框保持未勾选

#### Scenario: 样式记忆
- **WHEN** 操作者把「样式」下拉改为「红点」后关闭程序并重新打开
- **THEN** 下拉保持「红点」，随后运行的输出页为红点定位点

#### Scenario: 任务运行中禁用
- **WHEN** 排版任务运行期间
- **THEN** 勾选框与样式下拉均不可修改；任务结束后恢复可用
