# Spec Delta —— watermark-removal（去水印：功能取消，交外部人工处理）

## ADDED Requirements

### Requirement: 去水印不在本程序范围内
本程序 SHALL NOT 提供去水印功能：GUI 无去水印页签、CLI 无 `watermark` 子命令、`koutu/` 无去水印内核；水印处理 SHALL 由操作者在程序外使用外部工具（如豆包）人工完成。程序自动流程 SHALL 只读写 `原图 → 底图 → 已排版`，SHALL NOT 自动读写 `无水印*` 等保留目录。

#### Scenario: 主程序范围核对
- **WHEN** 打开主窗口或查看 CLI 子命令列表
- **THEN** 仅有两页签（抠图 / 排版）与 `cutout / layout` 两个子命令，无任何去水印入口

#### Scenario: 外部处理后继续
- **WHEN** 操作者用豆包等外部工具完成水印处理后把结果图人工放入保留目录（如 `doubao`）
- **THEN** 可用 `koutu cutout --src doubao --dst 底图` 等自定义目录方式继续后续流程；程序本身不感知、不处理水印

### Requirement: W3 研究留档与不采用声明
W3 去水印研究（`docs/水印研究.md`、`spike/watermark_research/`）SHALL 保留为留档并标注「未采用」；旧去水印产物（`无水印* / 无水印底图 / 去水印_预览 / 水印诊断` 等）SHALL NOT 用于通过/失败判定，验收 SHALL NOT 设去水印阶段。

#### Scenario: 验收范围
- **WHEN** 对照 `docs/验收清单.md` 执行验收
- **THEN** 阶段 3（去水印）为「已取消（不在范围）」不参与签收；阶段 0 / 1 / 2 / 4 判定不受影响

## REMOVED Requirements

### Requirement: 细纹压制去水印（detex.py）
**Reason**: 去水印功能整体取消（2026-10-06 使用者决定交豆包人工处理）；脚本归档 `legacy/`。
**Migration**: 不适用（不再有替代实现）。

### Requirement: 处理量度输出
**Reason**: 去水印功能整体取消；统计行不再存在。
**Migration**: 不适用。

### Requirement: 点阵印记检出与相位拟合（remove_watermark.py）
**Reason**: 去水印功能整体取消；W3 测绘研究（`docs/水印研究.md`）留档不采用。
**Migration**: 脚本归档 `legacy/`。

### Requirement: 按格扣除与幅度上限
**Reason**: 去水印功能整体取消；相关参数体系不再存在。
**Migration**: 不适用。

### Requirement: 透明通道保护
**Reason**: 该约束原本面向去水印路径；程序不再提供去水印，抠图/排版自身的 alpha 语义见对应能力规格。
**Migration**: 不适用（无去水印路径）。

### Requirement: AI 重绘路线（可选）
**Reason**: 程序不做 AI/在线去水印（非目标）；且自 2026-10-06 起水印整体交外部人工处理。
**Migration**: `remove_watermark_ai.py` 归档 `legacy/`。

### Requirement: AI 重绘路线的隔离与容错
**Reason**: 同上，路线移除。
**Migration**: 不适用。

### Requirement: 处理报告
**Reason**: 去水印功能整体取消；报告语义不再存在。
**Migration**: 不适用。
