# Spec Delta —— pipeline-orchestration（流程契约：单程序载体）

## ADDED Requirements

### Requirement: 数据目录契约与保留名单
新程序的自动流程 SHALL 只读写三个环节目录：`原图 → 底图 → 已排版`（输出目录不存在时自动创建）。全部历史中文目录名——`原图 / 原图_去水印 / doubao / 底图 / 无水印 / 无水印_AI重绘 / 无水印_精修 / 无水印_细纹轻 / 无水印_细纹重 / 无水印底图 / 去水印_预览 / 已排版 / 水印诊断`——SHALL NOT 被重命名或删除；未来新增产物 SHALL 优先复用保留名单中的名字。`原图_去水印`、`doubao`、`无水印_AI重绘`、`无水印_精修`、`无水印底图`、`去水印_预览`、`水印诊断` 等保留为人工/历史用途，不参与自动流程。

#### Scenario: 换批次不影响契约
- **WHEN** 操作者把「底图」内容整体换成另一批徽章
- **THEN** 直接运行排版即可，无需改动任何配置或目录名

#### Scenario: 保留名单逐项核对
- **WHEN** 检查程序运行后的目录结构
- **THEN** 13 个历史目录名全部原样存在（不重命名、不删除；新增的只有保留名单内的名字）

### Requirement: 程序根目录定位
所有读写入口 SHALL 以「程序根」为工作根：打包版 = 主程序 `koutu.exe` 所在目录；源码版 = 仓库根。相对路径按该根解析，绝对路径直接使用；SHALL NOT 依赖当前工作目录，SHALL NOT 写死绝对路径；资源（`排版demo.png`）、日志与设置文件 SHALL 相对该根定位。

#### Scenario: 整目录搬迁
- **WHEN** 把交付目录拷到另一台 Windows 电脑
- **THEN** 双击 `koutu.exe` 即可运行，无需安装或改配置

#### Scenario: 任意 cwd 启动一致
- **WHEN** 从不同工作目录以绝对路径启动程序
- **THEN** 读写行为一致（不读当前工作目录下的任何文件）

### Requirement: 运行日志与统计行
两个能力 SHALL 把运行日志写入程序根下的固定文件名：`运行日志.txt`（抠图）、`排版日志.txt`（排版），编码 UTF-8。日志 SHALL 包含输入/输出目录、关键参数、逐文件处理结果与汇总统计；统计行 SHALL 保留可核对语义（圆心/半径/尺寸、槽位数/页数/分配表），作为验收证据。

#### Scenario: 事后追溯
- **WHEN** 某张图处理失败
- **THEN** 对应日志含 `[失败] 文件名 原因` 行与成功/失败汇总

#### Scenario: 两份日志齐全
- **WHEN** 分别运行两个能力（抠图 / 排版）
- **THEN** 两份日志均生成在程序根，关键统计行不缺失

### Requirement: 单程序入口与退出码
操作入口 SHALL 为一个主程序：双击 = GUI（两页签）；命令行 = 子命令（`cutout / layout`），GUI 与 CLI 共用同一核心实现与同一日志。CLI 退出码 SHALL 统一为：全部成功 0 / 有文件失败 1 / 未捕获异常 2。旧 `.bat` 入口 SHALL NOT 随新交付（历史入口保存在 `legacy/`）。

#### Scenario: 双击即用
- **WHEN** 操作者首次双击 `koutu.exe`
- **THEN** 打开两页签主窗口，首次运行自动创建数据目录

#### Scenario: CLI 批处理
- **WHEN** 执行 `koutu cutout`（或其余子命令）
- **THEN** 无界面完成批处理，退出码与日志符合契约

## REMOVED Requirements

### Requirement: 目录契约稳定
**Reason**: 语义保留，载体从「脚本之间的接口」改为「单程序内部 + 操作者文件接口」。
**Migration**: 见新需求「数据目录契约与保留名单」。

### Requirement: 一键流程入口
**Reason**: 多个 `.bat` 双击入口退役，收敛为单程序。
**Migration**: 双击 `koutu.exe` 使用 GUI；旧 `.bat` 存入 `legacy/`。

### Requirement: 豆包在线去水印衔接流程
**Reason**: 程序不做去水印（含 AI/在线路线）；水印由操作者用豆包等外部工具人工处理，衔接流程不随程序交付。
**Migration**: `doubao` 等保留目录名不变；外部处理结果可人工放入后用 `koutu cutout --src doubao --dst 底图` 等自定义目录方式继续。

### Requirement: 脚本根目录定位
**Reason**: 载体更新为单程序，语义保留并明确打包/源码两种根。
**Migration**: 见新需求「程序根目录定位」。

### Requirement: 运行日志
**Reason**: 语义保留，日志集合更新（`_layout_log.txt` 退役；去水印日志不再新增）。
**Migration**: 见新需求「运行日志与统计行」。
