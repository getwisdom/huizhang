# 提案：layout-anchors —— 排版定位点（照模板绘制小三角；默认开、可关）

## Why

- **操作者需求（使用者已拍板）**：排版输出页 `已排版\第N页.png` 需要为每个槽位加一枚「定位点」——即模板 `排版demo.png` 每个圆形内侧正上方已有的黑色空心小三角（尖朝上、紧贴圆内缘），用于付印对齐；位置/样式以模板实物为准。
- 现状：输出页 = 白底 + 徽章，模板只参与槽位识别（`koutu/core/layout.py`）；模板上的小三角不会出现在输出页，需要本变更主动搬运。

## What Changes

- **排版内核（badge-layout）**：为每个槽位（**含空槽**）绘制定位点——从模板提取「小三角所在小区域」（相对槽位中心的 40×19px 补丁，实测见 design.md），以**含底**叠法（原样搬运；含底为默认）叠加到输出页同一相对位置；**默认开启、可关闭**；换模板而无此标记时**安全降级**（不绘制、不报错、日志一句）。排版日志保留既有统计行语义，追加一行标注定位点开关状态与绘制数量。
- **破坏性评估**：**BREAKING（默认行为变更）**——默认开启后输出页像素新增定位点；目录契约、输出文件名、默认目录均不变。迁移/复现旧基线：CLI `--no-anchors` 或 GUI 取消勾选；`docs/验收清单.md` 阶段 2 回归命令补 `--no-anchors`。
- **CLI（pipeline-orchestration）**：`koutu layout` 新增 `--anchors / --no-anchors`（默认开启，语义与 GUI 一致）。
- **GUI（desktop-gui）**：「排版」页签新增「添加定位点」勾选框——默认勾选、随现有 QSettings 机制记忆（`layout/anchors`）、任务运行中禁用。
- **对照/测试**：关闭时阶段 2 golden 复跑（尺寸/页数/分配表/像素阈值照旧）；新增 pytest——补丁窗口裁剪区域与模板逐像素一致（含空槽）、开关行为、降级、CLI 开关、GUI 勾选框与记忆；另出「含底 / 去底 / 关闭」对照样张交使用者目检（停2）。

### 非目标（Non-Goals）

- 不绘制圆环或模板其他元素、不做任何美化；只搬运「三角所在小区域」。
- 不改槽位识别、合成插值、清空输出目录、日志既有统计行等既有行为；不改目录契约与输出文件名。
- 不做「只给已放徽章的槽画定位点」默认切换（默认空槽也画；使用者一句话可改）。
- 不改去水印占位；不碰 `legacy/`、`golden/`、已归档变更与 13 个数据目录。

## Capabilities

### Modified Capabilities

- `badge-layout`：新增需求「定位点绘制（默认开启、可关闭）」——绘制 / 含空槽 / 降级 / 日志行。
- `desktop-gui`：新增需求「排版定位点开关（勾选框与记忆）」——默认勾选 / 记忆 / 运行中禁用。
- `pipeline-orchestration`：新增需求「排版定位点 CLI 开关」——`--anchors/--no-anchors` 默认开启、与 GUI 同语义。

## Impact

- 变更产物：`openspec/changes/layout-anchors/`（proposal / specs×3 / design / tasks）。
- 实现（批准后）：`koutu/core/layout.py`、`koutu/cli/main.py`、`koutu/gui/pages.py`、`koutu/gui/main_window.py`、`koutu/gui/worker.py`、`tests/`。
- 文档/验收：`docs/验收清单.md`（阶段 2 命令补 `--no-anchors` + 新增定位点判据）、`使用说明.txt`、`README.md`（必要时）。
- 交付：`packaging\打包.ps1` 重建 `dist\koutu\` 并冒烟（中文+空格路径；开/关各一页）。
- 保持：13 个数据目录零改动、`golden/`、`legacy/` 只读；本变更 delta 全为 ADDED 新增需求，归档合并向后兼容。
