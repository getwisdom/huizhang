# badge-layout Specification

## Purpose

把「底图」目录里抠好的圆形徽章 PNG，按模板图 `排版demo.png` 上自动识别出的圆形槽位排成整页，
输出可直接付印的多页 PNG。

阶段定义：`底图/*.{png,jpg,jpeg,bmp,gif}` + `排版demo.png` → `已排版/第N页.png`

实现：`koutu/core/layout.py`（Python 单实现）；GUI「排版」页签与 CLI `koutu layout`（见 `desktop-gui` 规格）。

## Requirements

### Requirement: 模板槽位识别
系统 SHALL 从模板图 `排版demo.png` 自动识别圆形槽位，操作者不需要手工配置版面。定位 SHALL 通过连通域完成：以步长 4 降采样，前景判据 `|R-255| + |G-255| + |B-255| > 60`（白底模板），4 邻域连通域求包围盒；采样点数 <300 的连通域丢弃；两包围盒交并比 >0.3 时合并；槽位 SHALL 按包围盒顶边 y 升序、再按左边 x 升序排序（以包围盒坐标为准而非圆心坐标——冻结基线的底行两槽即为先右后左，必须复刻）。每个包围盒外扩 6px 后用中心十字弦法拟合圆（半径 ≤10 视为失败丢弃）；半径 <300px 的圆丢弃；识别不到任何槽位时 SHALL 报「模板上没有识别到圆形槽位,请检查 排版demo.png」语义错误。

#### Scenario: 当前 A4 模板
- **WHEN** 用 2480×3508 白底、含 11 个圆形徽章位的 `排版demo.png`
- **THEN** 识别出 11 个槽位，每个槽位直径 828 像素（r=414）

#### Scenario: 换版面
- **WHEN** 操作者把 `排版demo.png` 换成另一张白底模板
- **THEN** 槽位按新模板重新识别，每页张数随之改变，无需改代码或配置

### Requirement: 底图读取与圆形区域定位
系统 SHALL 用 32 位 ARGB 读取底图，并以 alpha 包围盒定位徽章圆形区域：圆形区域取 alpha > 16 的像素包围盒，圆心 = 包围盒中心，半径 = `max(包围盒宽, 包围盒高) / 2`。完全不含 alpha > 16 像素的文件 SHALL 被跳过并记入日志；扩展名不在 `png / jpg / jpeg / bmp / gif` 内的文件 SHALL 被忽略；跳过全部底图后无可用图片时 SHALL 报「底图文件夹里没有可用图片」语义错误。

#### Scenario: 混入全透明空图
- **WHEN** 「底图」里有一张 alpha 全为 0 的 PNG
- **THEN** 该文件被跳过并记录原因，其余图片正常排版

### Requirement: 自然序填充与分页
每页槽位数 SHALL 等于模板识别出的槽位数；底图 SHALL 按文件名 Windows 自然序（`StrCmpLogicalW` 等价）排序后依次填槽：第 `1..N` 张填入第 1 页、第 `N+1..2N` 张填入第 2 页（N = 每页槽位数）；页内按「模板槽位识别」确定的槽位顺序依次填入；最后一页不足时多余槽位 SHALL 留白，不得报错。

#### Scenario: 7 张底图 + 11 槽模板
- **WHEN** 「底图」有 7 张图、模板有 11 个槽位
- **THEN** 只生成 1 页 `第1页.png`，第 8–11 个槽位留白

#### Scenario: 自然序不被打乱
- **WHEN** 「底图」含 `1.png`、`2.png`、`10.png`、`11.png`
- **THEN** 填充顺序为 1 → 2 → 10 → 11，而不是字典序的 1 → 10 → 11 → 2

### Requirement: 页面合成与缩放
输出画布尺寸 SHALL 等于模板尺寸（当前 2480×3508），底色 SHALL 为白色（`#FFFFFF`）。每张徽章 SHALL 按 alpha 包围盒裁出（四周各留 1 像素余量），绘入对应槽位的外接正方形（边长 = 2 × 槽位半径 + 2），保持圆形居中；缩放 SHALL 使用高质量双三次插值（`HighQualityBicubic` + `HighQuality` 像素偏移），透明背景原样保留（源叠加合成）。写入前 SHALL 清空输出目录旧的 `*.png`，避免残留上一次运行的旧页。

#### Scenario: 输出尺寸与模板一致
- **WHEN** 模板为 2480×3508
- **THEN** 每个 `第N页.png` 均为 2480×3508、白底

#### Scenario: 重复运行
- **WHEN** 第二次运行排版
- **THEN** 输出目录里旧页面先被删除，只留下本次生成的页

### Requirement: 输出文件与排版日志
页面 SHALL 写为 `已排版/第N页.png`（N 从 1 开始，无零填充、无日期前缀）。排版 SHALL 把日志写入程序目录 `排版日志.txt`（UTF-8），同时输出到控制台（可用时）；日志 SHALL 至少包含：模板尺寸、识别到的槽位数、有效底图数量（跳过无效文件后）、总页数、逐页生成路径，以及逐槽位分配表（`p1 slot# 1 (475,449) <- 1.png` 语义等价）。

#### Scenario: 对照基线分配表
- **WHEN** 用基线 7 张底图排版
- **THEN** `排版日志.txt` 的页数与分配表与 `golden/logs/run_final/_layout_log.txt` 逐行一致（`pages: 1 (11 per page)` 与 7 行 `p1 slot# … <- …`，坐标容差 ±2px）

### Requirement: CLI 子命令与金标准验收判据
系统 SHALL 提供 `layout` 子命令：`--demo`（默认 `排版demo.png`）、`--src`（默认 `底图`）、`--dst`（默认 `已排版`）；相对路径按程序根解析；退出码语义与抠图一致（0 / 1 / 2）。验收 SHALL 按 `docs/验收清单.md` 阶段 2 对照 golden：输出文件数与基线一致；尺寸 2480×3508 精确；页数与槽位分配表逐行一致；像素级对照采用与抠图相同的草案阈值。

#### Scenario: 基线对照
- **WHEN** 用基线数据排版并对照 `golden/baseline_products/已排版/第1页.png`
- **THEN** 上述判据全部通过（当前 1 页、7 行分配表）

#### Scenario: 自定义目录
- **WHEN** 执行 `koutu layout --src 底图 --dst 已排版`
- **THEN** 只影响本次读写的目录，模板缺省仍取程序根的 `排版demo.png`
