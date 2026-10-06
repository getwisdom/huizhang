# Spec Delta —— desktop-gui（排版定位点勾选框）

## ADDED Requirements

### Requirement: 排版定位点开关（勾选框与记忆）
「排版」页签 SHALL 提供「添加定位点」勾选框，默认勾选；勾选状态 SHALL 随现有 QSettings 机制记忆（键 `layout/anchors`；程序根 `koutu.ini`，不可写时回退 `%APPDATA%\koutu\koutu.ini`）并在重开程序时恢复；任务运行期间勾选框 SHALL 被禁用（不可修改），任务结束后恢复；勾选语义 SHALL 与 CLI `--anchors / --no-anchors` 一致。

#### Scenario: 默认勾选
- **WHEN** 全新环境首次启动程序
- **THEN** 「添加定位点」处于勾选状态

#### Scenario: 记忆保持
- **WHEN** 操作者取消勾选后关闭程序并重新打开
- **THEN** 勾选框保持未勾选

#### Scenario: 任务运行中禁用
- **WHEN** 排版任务运行期间
- **THEN** 勾选框不可修改；任务结束后恢复可用
