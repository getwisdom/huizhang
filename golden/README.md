# golden —— 金标准冻结（旧工具行为对照基线）

- 冻结时间：2026-10-05（Asia/Shanghai，UTC+8）
- 运行环境：Windows 11（10.0.22631）/ Windows PowerShell 5.1 / .NET Framework 4.8；本机无 Python、无 git
- 冻结方式：整个仓库拷贝到仓库外 `D:\workspace\_koutu_golden`（排除 .venv/.git/dist/build，实际均不存在），**所有"跑旧工具"只在副本里进行**；原仓库数据目录全程零改动
- 旧工具在副本中的运行记录（命令 / 耗时 / 退出码 / 日志统计行原文）：见 [`runbook.md`](./runbook.md)

## 目录索引（每个文件对照什么）

### checksums/ —— 校验和清单（SHA256；列：RelPath, Length, LastWriteTimeUtc, SHA256）

| 文件 | 对照什么 |
| --- | --- |
| `original_data_before.csv` / `original_data_after.csv` | 原仓库 13 个数据目录（原图 / 原图_去水印 / 底图 / 已排版 / 无水印 / 无水印_细纹轻 / 无水印_细纹重 / 无水印_精修 / 无水印_AI重绘 / 无水印底图 / 去水印_预览 / 水印诊断 / doubao）在"冻结开始前 / 全部跑完后"的状态；**两者必须一致 = 原仓库零改动**（本次 66 行、0 差异） |
| `original_data_diff.csv` | 上述对比结果（当前 0 行 = 无差异） |
| `copy_data_before.csv` | 副本刚拷贝完成、尚未跑工具前的状态（与 `original_data_before.csv` 逐字节一致 → 证明拷贝忠实） |
| `copy_data_after.csv` | 副本跑完旧工具后的状态 = **新工具验收时的对照基线**（66 个文件） |
| `baseline_products_diff.csv` | 副本 before→after 差异 = 本批旧工具产出清单（8 项：底图 7 + 已排版 1；三个日志不计入数据目录清单，见全树对照） |
| `tree_diff_report.csv` | 全树对照（原仓库去 `golden\` vs 副本去 `_golden_run\`）：**只改了 8 个产物 + 3 个日志，其余 113 个文件逐字节未动**，无新增/丢失 |
| `repo_tree_except_golden.csv` / `copy_tree_except_run.csv` | 全树对照两侧的完整清单（各 124 行） |
| `tools_binaries.csv` | 旧工具身份冻结：徽章抠图.exe、排版工具.exe、抠图工具.cs、排版工具.cs、cut_badge.ps1、layout.ps1、各 .bat 及辅助脚本共 18 个文件的 SHA256 |
| `consistency/` | 确定性 / 双实现一致性中间快照（H0=B1 产物、H1=A2、H2=B2、已排版 before/C/D），用于复核"逐字节一致"结论 |

### baseline_products/ —— 冻结基线产物本身（从副本原样复制）

| 路径 | 对照什么 |
| --- | --- |
| `底图/1.png…6.png、测试_1.png` | 抠图阶段基线：7 张透明 PNG（`徽章抠图.exe --batch` 与 `cut_badge.ps1` 双实现产物逐字节一致；与仓库内旧 底图 **像素级完全一致、编码层不同**） |
| `已排版/第1页.png` | 排版阶段基线：2480×3508 页（`排版工具.exe` 与 `layout.ps1` 产物逐字节一致） |
| `运行日志.txt` / `排版日志.txt` / `_layout_log.txt` | 同上三份日志的副本（原文也保存在 `logs/run_final/`） |

### logs/ —— 运行日志与过程记录

| 路径 | 说明 |
| --- | --- |
| `pre_run/` | 冻结时仓库里原有的三个日志（历史状态，作者机器 `C:\Users\leafr\Desktop\koutu` 时代）；注意旧 `_layout_log.txt` 是更早的"14 张底图 / 2 页"记录 |
| `run_final/` | 本批冻结跑完后副本里的最终日志（= 基线日志） |
| `steps/` | 每一步的输出/日志快照：A_badge_exe、B_cut_ps1、A2_badge_exe、B2_cut_ps1、C_layout_exe、D_layout_ps1（stdout.txt / changed_files.csv / 该步写入的日志） |
| `copy_robocopy.log` | 仓库→副本拷贝日志（124 文件 / 86.39 MB / 0 失败） |
| `run_steps.jsonl` | 单步机读记录（命令、用时、退出码、变更文件数；含首跑与装置自检，详见 runbook.md 备注） |

### tools/ —— 旧工具身份锚点副本

冻结当时的二进制与源码副本（与仓库根目录同名文件逐字节一致）：
徽章抠图.exe、排版工具.exe、抠图工具.cs、排版工具.cs、cut_badge.ps1、layout.ps1、抠图.bat、排版.bat

### scripts/ —— 验收复用脚本

| 脚本 | 用途 |
| --- | --- |
| `hash-tree.ps1` | 生成目录 SHA256 清单 CSV（`-Base / -Out / -Include`） |
| `compare-manifests.ps1` | 比对两份清单（退出码 0=一致 / 1=有差异；用 `powershell -File` 调用） |
| `pixel-diff.ps1` | 像素级对照（不透明像素数、alpha 差、RGB 差；内联 C#，大图也快） |
| `run_step.ps1` | 冻结用单步运行器 v2（历史保留；v1 缺陷与重跑见 runbook.md） |

## 关键结论（决定验收方式，务必先读）

1. **抠图双实现 + 重复运行 = 逐字节一致**：B1（cut_badge.ps1 首跑）≡ A2（徽章抠图.exe 重跑）≡ B2（cut_badge.ps1 重跑），8/8 文件 SHA256 相同；A1（首跑）输出尺寸与三者一致。
2. **排版双实现 = 逐字节一致**：`排版工具.exe` 与 `layout.ps1` 的 `第1页.png` SHA256 相同。
3. **原仓库零改动**：13 个数据目录 66 个文件 before/after 全等；全树对照显示运行只修改了预期的 8 个产物 + 3 个日志。
4. **⚠ 不要用逐字节 SHA 对照仓库里的旧产物**：仓库内旧 `底图`、`已排版` 与新产物 SHA256 不同，但**像素级完全一致**（底图 7/7、页 1/1：alpha 差>8 的像素=0、RGB 差>8 的像素=0）。旧文件属于历史编码版本；行为对照一律走像素级 + 日志统计行。
5. 旧 `_layout_log.txt`（pre_run）记录的是 14 张底图 / 2 页的旧运行；本基线为 7 张 / 1 页——对照时以 `logs/run_final/` 为准。

## 容差建议草案（验收用；待与主 agent 确认后固化）

> 前提：旧工具自身重放为 0 差异；以下为面向"新 Python 实现"的初始容差，稳定后可收紧。

**抠图**（对照 `baseline_products/底图/` 与 `logs/run_final/运行日志.txt`）：

- 输出文件名集合一致；图像宽高一致；
- 不透明像素数（alpha>0）：**±0.5%**（任务给定）；
- 圆心 **±2px**、半径 **±2px**（对照日志统计行 `圆心(x,y) 半径r` 与 `circle=(cx=..,cy=..,r=..)`）；
- 像素级（pixel-diff.ps1）：alpha 差>8 的像素占比 ≤0.5%、最大 alpha 差 ≤64、双方可见像素 RGB 差>8 占比 ≤0.5%（草案，暂宽）。

**排版**（对照 `baseline_products/已排版/第1页.png` 与 `logs/run_final/_layout_log.txt`）：

- 输出尺寸 **2480×3508 精确**；
- 页数一致（`pages: N (11 per page)`）；槽位分配表逐行一致（`p1 slot# 1 (475,449) <- 1.png` …）；
- 像素级：与抠图同草案阈值（整页 8,699,840 像素）。

**去水印**：**旧输出不作数**（仓库 `无水印*/无水印底图/去水印_预览/水印诊断` 等产物仅作历史参考，不参与通过/失败）；指标待模块定稿，占位见 `docs/验收清单.md`。

## 维护说明

- 副本 `D:\workspace\_koutu_golden` 是操作场地与完整档案（含 `_golden_run` 过程记录：逐步哈希快照、C 版页面副本等）；`golden/` 是入库的冻结精简集（本目录 72 个文件 / 约 12.1 MB）。
- 新工具的输出请写到运行目录的 `底图`、`已排版` 等，与 `copy_data_after.csv` / `baseline_products` 对照；对照命令见 `docs/验收清单.md`。
- 冻结批次的"首跑"记录说明：装置 v1 在 PowerShell 5.1 下无法捕获退出码，已用 v2 重跑补齐（产物与首跑逐字节一致）；细节见 `runbook.md`。
