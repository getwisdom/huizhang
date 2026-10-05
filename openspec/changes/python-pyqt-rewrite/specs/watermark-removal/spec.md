# Spec Delta —— watermark-removal（去水印：从零重新设计）

## ADDED Requirements

### Requirement: 去水印阶段契约
系统 SHALL 读取「底图」、把结果以同名 `.png` 覆写写入「无水印」（输出目录不存在时自动创建）；单张失败 SHALL 记录原因并继续处理后续图片；输入目录无受支持图片时 SHALL 给出非零退出码语义并提示。若未来提供分档输出，SHALL 复用既有保留目录名（`无水印_细纹轻` / `无水印_细纹重`），不得新造目录名。

#### Scenario: 默认批处理
- **WHEN** 对「底图」执行去水印
- **THEN** 「无水印」得到同名 PNG，逐张统计行与汇总可用

#### Scenario: 空目录与单张失败
- **WHEN** 输入目录为空，或批内某张图失败
- **THEN** 空目录提示并返回非零码；单张失败不影响其余图片继续处理

### Requirement: 透明通道逐像素保持
所有去水印路径 SHALL 保持输入 alpha 通道逐像素不变，输出为 RGBA PNG；圆形之外的透明区域与边缘羽化带 SHALL NOT 被硬化或涂抹。

#### Scenario: 已抠好的圆形徽章
- **WHEN** 输入是「底图」里带羽化边缘的透明 PNG
- **THEN** 输出在圆形之外仍然透明，alpha 与输入逐像素一致

### Requirement: 确定性与离线
同一输入 + 同一参数 SHALL 每次得到相同的输出（可复现）；处理 SHALL NOT 依赖网络或任何外部服务；AI 重绘与在线路线为非目标，不存在于本程序。

#### Scenario: 重跑一致
- **WHEN** 同一张图连续处理两次
- **THEN** 两次输出逐像素一致

#### Scenario: 断网可用
- **WHEN** 在没有网络的机器上运行
- **THEN** 去水印功能不受影响

### Requirement: 局部扣除与幅度边界
修改 SHALL 只发生在检出/建模的水印位置；SHALL 只修改 RGB（alpha 不动）、结果夹取到 0–255；SHALL NOT 对全图做几何变换或整体色调变换。扣除幅度上限与默认参数 SHALL 在研究波次（本变更 tasks.md 的 W3）定稿后回写本规格；定稿前，默认参数以基线样张人工确认「无明显可见残留且非水印区域无可见损伤」为准。

#### Scenario: 非水印区域保真
- **WHEN** 处理一张含淡水印的底图
- **THEN** 非水印区域的像素改动量低于测定门槛（门槛随 W3 定稿写入），画面无可见损伤

### Requirement: 统计行与去水印日志
每张图 SHALL 输出可核对的统计行（水印幅度降幅与改动量级，语义对齐旧「处理量度输出」），并写入程序目录 `去水印日志.txt`（UTF-8）；数值门槛由研究波次定稿后写入本规格。

#### Scenario: 判断强度是否过度
- **WHEN** 查看 `去水印日志.txt`
- **THEN** 每张图可见降幅与改动量级统计，可据此判断是否存在过度扣除

### Requirement: CLI 子命令（去水印）
系统 SHALL 提供 `watermark` 子命令：`--src`（默认 `底图`）、`--dst`（默认 `无水印`）；相对路径按程序根解析；退出码语义与全程序一致（0 / 1 / 2）。具体参数名与默认值 SHALL 在研究波次定稿后回写本规格。

#### Scenario: 默认路径批处理
- **WHEN** 执行 `koutu watermark`
- **THEN** 处理「底图」并输出到「无水印」，退出码与统计行符合契约

#### Scenario: 自定义目录
- **WHEN** 执行 `koutu watermark --src 底图 --dst 无水印`
- **THEN** 只影响本次读写的目录，其它目录不被改动

### Requirement: 旧输出不作数与指标定稿机制
旧去水印产物（仓库 `无水印* / 无水印底图 / 去水印_预览 / 水印诊断` 等）SHALL NOT 用于通过/失败判定。验收指标（水印幅度降幅阈值、非水印区保真门槛、OCR 复核候选）SHALL 由研究波次定稿后写入 `docs/验收清单.md` 阶段 3 与本规格，其后才开始阶段 3 签收。

#### Scenario: 阶段 3 定稿
- **WHEN** 研究波次提交「命令 + 数值门槛 + 1–2 张人工目检记录」
- **THEN** 阶段 3 判据齐备并回写本规格；在定稿前阶段 3 不签收

## REMOVED Requirements

### Requirement: 细纹压制去水印（detex.py）
**Reason**: 旧路线不作基准，去水印从零重新设计；脚本归档 `legacy/`。
**Migration**: 新设计见本能力新增需求；历史实现仅作参考，不参与验收。

### Requirement: 处理量度输出
**Reason**: 载体退役，统计行语义保留。
**Migration**: 见新需求「统计行与去水印日志」；σ 口径可作 W3 研究参考。

### Requirement: 点阵印记检出与相位拟合（remove_watermark.py）
**Reason**: 旧路线不作基准，从零重新设计（水印域事实由 W3 重新测绘）。
**Migration**: 脚本归档 `legacy/`；相位/点阵等细节不再继承。

### Requirement: 按格扣除与幅度上限
**Reason**: 旧参数（1.0–16.0 / 18.0 灰度级）属于旧实现，不作新基准。
**Migration**: 幅度边界改由新需求「局部扣除与幅度边界」+ W3 定稿的门槛承载。

### Requirement: 透明通道保护
**Reason**: 语义保留并加强为所有路径的硬约束。
**Migration**: 见新需求「透明通道逐像素保持」。

### Requirement: AI 重绘路线（可选）
**Reason**: AI 去水印为非目标，路线整体移除。
**Migration**: `remove_watermark_ai.py` 归档 `legacy/`；ComfyUI 依赖不再存在。

### Requirement: AI 重绘路线的隔离与容错
**Reason**: 同上，AI 路线移除，隔离/容错问题不再存在。
**Migration**: 不适用。

### Requirement: 处理报告
**Reason**: 语义并入新需求集合。
**Migration**: 目录创建/逐张结果/统计见「去水印阶段契约」「统计行与去水印日志」。
