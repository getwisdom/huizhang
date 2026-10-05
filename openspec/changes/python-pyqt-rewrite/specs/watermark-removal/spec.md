# Spec Delta —— watermark-removal（去水印：入口占位，本版不实现算法）

## ADDED Requirements

### Requirement: 「去水印」页签占位
GUI SHALL 含「去水印」页签作为入口占位：页签存在且可切换，页内显示「功能后续版本提供」类中文说明；页签 SHALL NOT 提供可用的处理入口（占位禁用态）；切换与查看 SHALL NOT 读取、处理或写出任何文件（数据目录零动）。

#### Scenario: 页签存在与说明文案
- **WHEN** 打开主窗口并切换到「去水印」页签
- **THEN** 页签存在，显示「后续版本提供」类中文说明，无可用处理入口，程序不执行任何处理、不产生任何输出

### Requirement: CLI `watermark` 占位子命令
CLI SHALL 保留 `watermark` 子命令名作为占位：执行时输出「功能后续版本提供」类中文说明，并以非零退出码结束（本版取 2）；SHALL NOT 执行任何处理、不读写任何数据目录。

#### Scenario: 占位子命令的提示与退出码
- **WHEN** 执行 `koutu watermark`（源码版）或 `koutu.exe watermark`（打包版）
- **THEN** 输出中文说明，退出码为 2（非零）；不产生任何图片读写，数据目录零变化

### Requirement: 无水印目录保留与零自动写入
`无水印 / 无水印_AI重绘 / 无水印_精修 / 无水印_细纹轻 / 无水印_细纹重 / 无水印底图 / 去水印_预览 / 水印诊断` 等历史目录名 SHALL 保留（不可重命名、不可删除）；本版程序 SHALL NOT 自动读写这些目录（无自动写入者）；程序自动流程 SHALL 仍为 `原图 → 底图 → 已排版`。

#### Scenario: 运行后目录零动
- **WHEN** 完成任一 GUI / CLI 流程（含访问「去水印」页签与执行 `watermark` 占位子命令）后核对目录结构
- **THEN** 上述历史目录原样保留，程序未在其中新增、修改或删除任何文件

## REMOVED Requirements

### Requirement: 细纹压制去水印（detex.py）
**Reason**: 本版不实现去水印算法（入口占位，算法留待后续版本）；脚本归档 `legacy/`。
**Migration**: 后续版本启动时可参考 `spike/watermark_research/` 研究留档与 `legacy/detex.py`。

### Requirement: 处理量度输出
**Reason**: 本版无去水印处理，统计行不适用。
**Migration**: 不适用（后续版本实现时重新定稿）。

### Requirement: 点阵印记检出与相位拟合（remove_watermark.py）
**Reason**: 本版不实现去水印算法；W3 测绘研究（`docs/水印研究.md`）留档供后续版本启动。
**Migration**: 脚本归档 `legacy/`，只读参考。

### Requirement: 按格扣除与幅度上限
**Reason**: 本版无去水印处理，相关参数体系留待后续版本定稿。
**Migration**: 不适用。

### Requirement: 透明通道保护
**Reason**: 该约束原本面向去水印路径；本版无去水印处理，抠图/排版自身的 alpha 语义见对应能力规格。
**Migration**: 不适用（后续版本实现时沿用该约束）。

### Requirement: AI 重绘路线（可选）
**Reason**: AI/在线路线为非目标；且本版不实现去水印算法（入口占位）。
**Migration**: `remove_watermark_ai.py` 归档 `legacy/`。

### Requirement: AI 重绘路线的隔离与容错
**Reason**: 同上，路线移除。
**Migration**: 不适用。

### Requirement: 处理报告
**Reason**: 本版无去水印处理；报告语义留待后续版本。
**Migration**: 不适用。
