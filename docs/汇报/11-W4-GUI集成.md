# 汇报 11 —— W4 GUI 集成（三页签 / 实跑与证据）

- 产出人：开发工程师（W3–W6 承接）
- 日期：2026-10-06
- 依据：W4 补充指令（先落实 tasks 3.4/3.5 占位与旧口径清理，再推进 4.1–4.6）。
- 状态：**W4 完成并提交**；下一波 W5 打包与交付。

## ①任务与范围

- 补充项（先做）：
  1. **3.4 GUI 去水印占位页签**：页签存在，文案定稿一句「本功能后续版本提供」，占位禁用态（按钮禁用、无处理面），不执行任何处理；
  2. **3.5 CLI `watermark` 占位子命令**：保留命令名，中文提示，退出码 2，不读写任何目录；
  3. **旧口径清理**：`koutu/__init__.py` 模块说明改为三页签（含去水印入口占位）；`docs/水印研究.md`、`docs/汇报/09-W3-去水印实现.md` 各追加一行「【后续修订 2026-10-06】」注记（不动历史正文、不动 spike 留档）。
- 4.1–4.6：
  - 4.1 三页签骨架（抠图 / 排版 / 去水印占位）+ 只读路径展示 + 抠图参数 10–200 / 0–20（默认 45 / 4）；
  - 4.2 QSettings(IniFormat)：几何 / 页签 / 参数；程序根 `koutu.ini` 优先、不可写回退 `%APPDATA%\koutu\koutu.ini`；
  - 4.3 QThread 线程模型：`log_line / progress / finished / failed`；取消在「单张文件边界」生效；
  - 4.4 页签接 core：统计行原文显示、「打开输出目录」、保存失败重试（内核重试 + 落日志，不静默）；去水印页签不接 core；
  - 4.5 offscreen 冒烟纳入 pytest；`spike/qt_smoke.py` 留档不删；
  - 4.6 副本数据实跑三能力（去水印仅验占位交互）。
- 纪律执行：数据目录零改动（全部试验在副本运行目录 `D:\workspace\_koutu_w4`）；未动 `golden/`、`legacy/`、`spike/watermark_research/`；文件编码 UTF-8。

## ②命令/操作

1. 代码：新增 `koutu/gui/`（`__init__ / worker / pages / main_window`）；`koutu/cli/main.py` 增 `watermark` 占位；`koutu/__init__.py` 说明更新。
2. 测试：`.venv\Scripts\python.exe -m pytest tests -q` → **45 passed**（31 旧 + 14 新；新文件 `test_gui_smoke / test_gui_worker / test_config / test_cli_watermark`）。
3. CLI 实跑：`python -m koutu watermark` → 退出码 **2**、中文提示可读。
4. GUI 实跑（副本目录，程序根指向 `_koutu_w4`）：
   - offscreen 驱动 `drive_gui.py`（真实窗口栈 + QThread + 内核；7 张真图）：抠图（运行中切页签）→ 排版 → 去水印占位交互；
   - 真机开窗核验 `drive_gui.py --visible`：窗口可见 `isExposed=True`、三页签、占位文案与禁用态、约 4 秒自动关闭，退出码 0；
   - 证据留档（运行目录，不入库）：`_koutu_w4\evidence_offscreen.txt`、`evidence_visible.txt`、`运行日志.txt`、`排版日志.txt`、`koutu.ini`、`已排版\第1页.png`、`底图\*.png`（7 张）。
5. 零改动核对：仓库根 `运行日志.txt`（01:30）/`排版日志.txt` 未被本轮触碰；仓库根无 `koutu.ini`；`原图\`、`底图\` 文件 mtime 为 2026-10-04（未动）。
6. 勾选 tasks 3.4 / 3.5 / 4.1–4.6 与验收清单阶段 3 四条（含实测注记）；中文提交。

## ③关键数字

- pytest：**45 passed**（W4 新增 14 条，全绿）。
- 抠图实跑（GUI 链路，7 张真图）：**成功 7 / 失败 0**；统计行与基线一致（`1.jpg -> 1.png (OK 417x417 圆心(414,365) 半径200)`、`测试_1.jpg -> 测试_1.png (OK 492x492 圆心(397,421) 半径238)` 等）。
- 排版实跑：识别 **11 个槽位**、底图 7 张、共 **1 页**；分配表 7 行与 golden 基线一致（`p1 slot# 1 (475,449) <- 1.png` … `p1 slot# 7 (471,2190) <- 测试_1.png`）。
- 去水印占位：页签文案「本功能后续版本提供」、按钮可用=False；CLI 提示「去水印功能后续版本提供（本版仅保留入口占位，不执行任何处理）。」、退出码 2。
- 真机开窗核验：`isExposed=True`、退出码 0。
- 设置文件生成于副本程序根：`_koutu_w4\koutu.ini`（233 B）。
- 窗口标题：`koutu · 徽章处理工具`；页签：`['抠图', '排版', '去水印']`。

## ④产物清单

| 类别 | 文件 |
| --- | --- |
| 新增代码 | `koutu/gui/__init__.py`、`worker.py`、`pages.py`、`main_window.py` |
| 修改代码 | `koutu/cli/main.py`（watermark 占位）、`koutu/__init__.py`（说明） |
| 新增测试 | `tests/test_gui_smoke.py`、`test_gui_worker.py`、`test_config.py`、`test_cli_watermark.py` |
| 修改测试装置 | `tests/conftest.py`（offscreen + `qapp`）、`tests/helpers.py`（`pump_until`） |
| 文档 | `docs/水印研究.md`、`docs/汇报/09-W3-去水印实现.md`（各 +1 行注记）；`docs/验收清单.md` 阶段 3 勾选 + 实测注记；`tasks.md` 3.4/3.5/4.1–4.6 勾选 |
| 新增汇报 | 本文件 `docs/汇报/11-W4-GUI集成.md` |
| 运行目录证据（不入库） | `D:\workspace\_koutu_w4\`（驱动脚本、两份 evidence、日志、底图 7 张、已排版 1 页、koutu.ini） |
| 保持不动 | 13 个数据目录、`golden/`、`legacy/`、`spike/watermark_research/`（含 qt_smoke 留档） |

## ⑤未验证与风险

- **打包版未验**（W5 范围）：exe 双击、中文+空格路径、无 Python 会话、阶段 3 CLI 打包版复跑均留待 W5。
- **真人点击目视**：本波以 offscreen 全链路 + 真机自动开窗核验（`isExposed=True`）取证；未做鼠标人工点检，建议使用者闲时双击复看一眼（无阻塞）。
- **控制台编码**：Python 在管道重定向下按本机 cp936(GBK) 输出，PowerShell 捕获需 `PYTHONIOENCODING=utf-8` 才可读；交互式控制台直显不受影响（Windows 控制台 Unicode 接口）。证据文件均按 UTF-8 留存。
- **取消路径**：worker 级单测覆盖（假任务断言边界语义）；GUI 内真实长任务取消未做人工实跑触发（逻辑与单测同源）。
- **保存失败重试**：内核重试 + 日志（W1 既有实现），GUI 原样显示失败行与汇总；未主动构造保存失败场景。
- 阶段 0 / 1 / 2 全量复跑留待 W6；本波 `pytest` 已覆盖挂接 golden 的对照用例（45 passed）。

## ⑥待确认问题

1. 窗口标题定稿：现为「koutu · 徽章处理工具」；如需更短或改名，请在 W5 前指出（改一行）。
2. 去水印占位文案定稿：「本功能后续版本提供」（一句）；如需补充「算法在后续版本提供」之类的说明可再指示。
3. 「打开输出目录」按钮在运行前也可点击（目录缺失时自动创建后打开）；如需改为「任务结束后才可用」，请指示。
