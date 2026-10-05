# Tasks —— python-pyqt-rewrite（按波次编排）

> 门禁：本文件在提案批准（门禁 B）后开始执行；按波次推进，每波完成即提交（中文提交信息，提交前 `git status` 核对无数据目录 / `.venv`）。每波的验收记录追加到 `docs/汇报/`（执行者署名）。
> 容差唯一来源：`docs/验收清单.md` 与各能力规格；不得自创口径。
> **范围变更（2026-10-06）**：W3–W6 施工移交开发工程师（使用者指示「只处理架构级别」）。W1/W2 已交付并对照 golden 验收（`cff680a` / `56f93cf`）；W3 测绘结论与接手指引见 `docs/汇报/08-架构交接.md`。
> **范围变更（2026-10-06，之二）**：去水印功能取消——水印交豆包（外部工具）人工处理；W3 以研究留档结案（3.2–3.6 不再实施；已完成的选型/原型/样张均留档不采用），程序收敛为两页签两能力（抠图 / 排版）；规格 / 设计 / 验收清单已同步。

## 0. 立项与装置（批准后立即执行；不写产品代码）

- [x] 0.1 修订 `.gitignore`：删除 `golden/`、`docs/`、`tests/` 三行；新增忽略 `dist/`、`build/`、`去水印日志.txt`、`koutu.ini`；验证：`git status` 只出现预期变更，数据目录与 `.venv` 不在其中
- [x] 0.2 验收装置入库：`git add docs tests golden` 后提交（golden 含约 12.1MB 基线图；`*.exe` 维持忽略）；验证：`git ls-files` 含 `docs/验收清单.md`、`docs/汇报/`、`tests/test_smoke.py`、`golden/README.md`、`golden/baseline_products/已排版/第1页.png`
- [x] 0.3 归档旧实现到 `legacy/`：`git mv` 旧源码与脚本（清单见 design D6）、旧 `.bat` 入口、本地移动旧 `*.exe`；新增 `legacy/README.md`（历史状态 + 不参与验收 + 可只读排查）；验证：根目录不再有旧入口；`legacy/` 内容完整；数据目录零改动（阶段 0.1 命令通过）
- [x] 0.4 更新 `docs/验收清单.md` 阶段 0.2：对照路径改为 `legacy\`，与 `golden/checksums/tools_binaries.csv` 按内容哈希逐文件对应（忽略路径前缀）；验证：命令输出「差异数: 0」并留档
- [x] 0.5 按 design D11 更新 `AGENTS.md`、`PROJECT.md`、`openspec/config.yaml`（双实现/编译/无测试等表述改为单实现 + golden + pytest + PyInstaller）；验证：`openspec validate --strict --all` 全绿，且通读修订段无旧世界残留

## 1. 抠图内核（W1；对照 golden 阶段 1）

- [x] 1.1 建立 `koutu/` 包骨架与 `paths.py`（程序根、目录契约常量、日志/设置路径）、`config.py`；验证：`python -m koutu --version` 可运行；单测覆盖 frozen / 源码两种根解析（monkeypatch `sys.frozen`）
- [x] 1.2 `core/imaging.py`：numpy/PIL 加载（24/32 位）、PNG 保存（失败重试 + 落日志）、高质量缩放；验证：单测在临时目录往返读写 32 位 PNG（alpha 保持）
- [x] 1.3 `core/cutout.py` 扫描 + RANSAC + 精修（40 线、阈值 45、种子 2024、600 次、内点 4px、精修容差 5px）；验证：参数常量与规格逐项一致的单测 + 基线 7 张圆心/半径 ±2px（对照 `golden/logs/run_final/运行日志.txt`）
- [x] 1.4 `core/cutout.py` 羽化、裁切、输出（32 位 ARGB、线性羽化、边界夹取、RGB 原样）；验证：单测「圆内无空洞」（不透明像素与 π·r² 偏差 ≤0.5%）与输出尺寸（417×417 场景）
- [x] 1.5 `core/pipeline.py` 批次执行器（确定性遍历、失败隔离、汇总、进度/日志回调、协作式取消）；验证：单测「6 好 + 1 坏」批继续处理且汇总正确
- [x] 1.6 `cli/main.py` 的 `cutout` 子命令 + `运行日志.txt`（UTF-8、统计行语义等价）+ 退出码 0/1/2；验证：在独立运行目录实跑基线 7 张，日志逐张对照基线（±2px）、断言退出码
- [x] 1.7 pytest 对照测试挂接 golden（文件名集合 / 宽高 / 圆心半径 / 不透明 ±0.5% / alpha 差>8 ≤0.5% 等像素阈值）；验证：`.venv\Scripts\python.exe -m pytest tests -q` 全绿且不写生产目录
- [x] 1.8 实跑核对与记录：按 `docs/验收清单.md` 阶段 1 命令执行（含 `pixel-diff.ps1`），实测数字追加到 `docs/汇报/`；验证：阶段 1 判据逐项打勾

## 2. 排版内核（W2；对照 golden 阶段 2）

- [x] 2.1 `core/layout.py` 槽位识别（step=4 / 阈值 60 / 最小 300 / 合并 0.3 / 外扩 6 / 十字弦 / 半径下限 300，报错文案语义）；验证：单测对 `排版demo.png` 断言 11 槽、r=414；对无效模板断言报错
- [x] 2.2 `core/naming.py` Windows 自然序（`StrCmpLogicalW` via ctypes）+ 底图读取（ARGB、alpha>16 包围盒、扩展名白名单、全透明跳过并记日志）；验证：单测 `1,2,10,11` 顺序与跳过日志
- [x] 2.3 页面合成（模板尺寸白底、双三次、源裁 1px、目标 2r+2、清空旧页）与 `第N页.png` 输出；验证：单测 2480×3508 精确、重复运行先清空
- [x] 2.4 `cli` 的 `layout` 子命令 + `排版日志.txt`（含分配表 `p1 slot# 1 (475,449) <- 1.png` 语义）；验证：独立运行目录实跑，页数/分配表与 `golden/logs/run_final/_layout_log.txt` 逐行一致（坐标 ±2px）
- [x] 2.5 pytest 对照测试（尺寸精确 / 页数 / 分配表 / 像素阈值）；验证：pytest 全绿
- [x] 2.6 实跑核对与记录：按阶段 2 命令对照 `golden/baseline_products/已排版/第1页.png`；验证：判据打勾并留实测数字

## 3. 去水印研究（W3；**已取消**——交豆包人工处理，研究留档）

- [x] 3.1 水印域测绘：在独立目录（副本或 `spike/` 外新目录）测绘点阵几何、色差幅度、覆盖区域；产出 `docs/水印研究.md`；验证：间距/幅度/覆盖率数字可复核，脚本与输入留档；2026-10-06 结案：功能取消，留档不采用
- [ ] 3.2 方案选型：给出 2–3 条确定性候选与选型结论（含放弃理由）；验证：写入 `docs/水印研究.md` 并评审通过（已取消）
- [ ] 3.3 原型与基线样张：产出前后对比图与指标表；验证：样张目检无明显残留、非水印区无可见损伤（已取消）
- [ ] 3.4 指标与参数定稿：命令 + 数值门槛 + 1–2 张目检记录写入 `docs/验收清单.md` 阶段 3；回写本变更的 `watermark-removal` 规格与 design；验证：阶段 3 成为可执行判据；`openspec validate --strict --all` 全绿（已取消）
- [ ] 3.5 `core/watermark.py` 移植（确定性、alpha 逐像素不动、局部扣除、0–255 夹取、统计行）；验证：单测（重跑逐像素一致、alpha 不变）+ 基线样张指标达标（已取消）
- [ ] 3.6 `cli` 的 `watermark` 子命令 + `去水印日志.txt`；验证：独立运行目录实跑，统计行与汇总齐全、退出码断言（已取消）

> W3 结案说明：3.1–3.3 已完成成果（测绘、选型、原型/样张）留档于 `docs/水印研究.md` 与 `spike/watermark_research/`，均**不采用**；阶段 3 验收取消（见 `docs/验收清单.md`）。

## 4. GUI 集成（W4）

- [ ] 4.1 `gui/main_window.py` 两页签骨架 + 只读路径展示 + 参数控件（抠图 10–200 / 0–20，默认 45 / 4）；验证：offscreen 冒烟单测可建窗、页签齐全
- [ ] 4.2 `config.py` QSettings(IniFormat) 记忆（几何 / 页签 / 参数；不可写回退 `%APPDATA%\koutu\koutu.ini`）；验证：单测两种存储路径 + 重启恢复
- [ ] 4.3 `gui/worker.py` 线程模型（log / progress / finished / failed；取消在单张边界生效）；验证：单测驱动假任务断言信号序列与取消行为
- [ ] 4.4 两页签接 core（统计行原文显示、「打开输出目录」、保存失败重试提示）；验证：offscreen 端到端跑小样本目录
- [ ] 4.5 GUI 冒烟纳入 pytest（`QT_QPA_PLATFORM=offscreen`）；`spike/qt_smoke.py` 留档不删；验证：pytest 全绿
- [ ] 4.6 人工实跑：两能力（抠图 / 排版）各跑一遍（用副本数据），核对统计行与输出；验证：留档 `docs/汇报/`（截图或数字）

## 5. 打包与交付（W5；参照环境验证 §5–6 与验收清单阶段 4）

- [ ] 5.1 `packaging/koutu.spec` + `packaging/打包.ps1`（UTF-8 BOM；PS 5.1 可加载）；验证：脚本可重复执行、退出码 0
- [ ] 5.2 构建 `dist\koutu\`：exe + `_internal\`，并把 `排版demo.png`、`使用说明.txt` 拷到 exe 同级；验证：产物齐备、规模记录（与环境验证 §5.2 同量级）
- [ ] 5.3 中文 + 空格路径冒烟：整包复制后双击 + CLI 批处理；验证：启动 / 退出码 / 日志齐备（参照 §6 实测口径）
- [ ] 5.4 无 Python 会话模拟（清理 `PATH`）跑两条主流程；验证：过阶段 1 / 2 判据（对照命令同源码版）
- [ ] 5.5 重写 `使用说明.txt`（两能力 + CLI + 常见问题 + 日志位置）；更新 `README.md`；`排版工具使用说明.txt`、`总结文档.md` 归档 `legacy/docs/`；验证：文档命令逐条可执行、无过期入口
- [ ] 5.6 执行 `docs/验收清单.md` 阶段 4 全部勾选并留档；验证：勾选清单 + 记录数字

## 6. 评审与归档（W6）

- [ ] 6.1 全量回归：阶段 0.1 / 0.2（更新后命令）、阶段 1 / 2 / 4 复跑、`pytest tests -q` 全绿；验证：全部通过并记录实测数字
- [ ] 6.2 `openspec archive python-pyqt-rewrite` 归档本变更（合并 7 份 delta）；验证：退出码 0，`openspec validate --strict --all` 全绿
- [ ] 6.3 归档后文字清理：修订 5 份主规格的 Purpose / 工具表等非需求文字为单程序世界；验证：`openspec show` 通读无旧工具（exe/bat/csc）残留
- [ ] 6.4 最终汇报与红线复核：`docs/汇报/` 汇总（含各步提交哈希）、数据目录零改动、git 历史未改写、工作树干净；验证：留档复核命令输出
