# runbook —— 旧工具冻结运行记录（命令 / 耗时 / 退出码 / 日志统计行原文）

- 运行目录：`D:\workspace\_koutu_golden`（仓库外副本；原仓库只读，数据目录零改动）
- 运行方式：`golden/scripts/run_step.ps1` 逐步运行并留证；每步的完整 stdout / stderr / 变更文件清单在 `logs/steps/<步骤>/`
- 时间：2026-10-05 23:21–23:28（Asia/Shanghai，UTC+8）；副本拷贝 86.39 MB / 124 文件 / 0 失败
- 输入：`原图/` 7 张（1.jpg…6.jpg、测试_1.jpg）；模板：`排版demo.png`（2480×3508）

## 步骤总表

| 步骤 | 命令（工作目录 = 副本根） | 用时 | 退出码 | 产物 / 改动 |
| --- | --- | --- | --- | --- |
| A1 | `徽章抠图.exe --batch`（首跑，装置 v1） | 0.14s | 未捕获* | 底图 7 张 + 运行日志.txt |
| B1 | `powershell -ExecutionPolicy Bypass -File cut_badge.ps1`（首跑，装置 v1） | 0.37s | 未捕获* | 底图 7 张（不写日志文件，只写控制台） |
| A2 | 同 A1（装置 v2 重跑） | 0.12s | **0** | 底图 7 张 + 运行日志.txt |
| B2 | 同 B1（装置 v2 重跑） | 0.31s | **0** | 底图 7 张 |
| C | `排版工具.exe`（无参数） | 0.49s | **0** | 已排版\第1页.png + 排版日志.txt |
| D | `powershell -ExecutionPolicy Bypass -File layout.ps1` | 0.63s | **0** | 已排版\第1页.png + _layout_log.txt |
| S0 | 装置自检：`cmd /c exit 5` | 0.03s | 5（预期） | 无 |

\* 装置 v1 缺陷说明：PowerShell 5.1 的 `Start-Process -PassThru` 在"重定向 + NoNewWindow"组合下 `.ExitCode` 返回空（已用最小对照实验确证）。v2 改用 .NET `ProcessStartInfo` 直构，退出码可靠、stdout/stderr 按原始字节落盘。A1/B1 的产物有效，且与 A2/B2 逐字节一致（见下），因此未重做首跑产物，仅补运行记录。

## 确定性与双实现一致性（关键结论）

- **H0（B1 后）≡ H1（A2 后）≡ H2（B2 后）**：8/8 文件（底图 7 + 运行日志.txt）SHA256 全等；清单在 `checksums/consistency/`。
- **C ≡ D**：`已排版\第1页.png` SHA256 相同（排版双实现逐字节一致）。
- **与仓库旧产物**：SHA256 不同、**像素级一致**（底图 7/7、页 1/1：alpha 差>8 的像素=0、RGB 差>8 的像素=0，maxAlphaDiff=0）。
- 原仓库零改动：数据目录 66 文件 before/after 0 差异；全树对照中运行只动了 8 个产物 + 3 个日志，其余 113 文件逐字节未动。

## 日志统计行原文（逐步）

### A —— 徽章抠图.exe --batch（`运行日志.txt`，743 字节，UTF-8 BOM）

```
徽章抠图工具
原图: D:\workspace\_koutu_golden\原图 (7 张)
输出: D:\workspace\_koutu_golden\底图
参数: 扫描阈值=45  羽化=4px  边距=4px
------------------------------
[完成] 1.jpg -> 1.png  (OK 417x417 圆心(414,365) 半径200)
[完成] 2.jpg -> 2.png  (OK 416x415 圆心(412,364) 半径199)
[完成] 3.jpg -> 3.png  (OK 417x417 圆心(414,365) 半径200)
[完成] 4.jpg -> 4.png  (OK 417x417 圆心(414,364) 半径200)
[完成] 5.jpg -> 5.png  (OK 417x417 圆心(414,364) 半径200)
[完成] 6.jpg -> 6.png  (OK 416x415 圆心(414,365) 半径199)
[完成] 测试_1.jpg -> 测试_1.png  (OK 492x492 圆心(397,421) 半径238)
------------------------------
全部完成：成功 7 张，失败 0 张
```

### B —— cut_badge.ps1（控制台输出；该脚本不写日志文件，stdout 原文 685 字节）

```
==== 徽章抠图工具（圆形）====
原图: D:\workspace\_koutu_golden\原图 (7 张)
输出: D:\workspace\_koutu_golden\底图

[完成] 1.jpg -> 1.png  (OK 417x417 circle=(cx=414, cy=365, r=200))
[完成] 2.jpg -> 2.png  (OK 416x415 circle=(cx=412, cy=364, r=199))
[完成] 3.jpg -> 3.png  (OK 417x417 circle=(cx=414, cy=365, r=200))
[完成] 4.jpg -> 4.png  (OK 417x417 circle=(cx=414, cy=364, r=200))
[完成] 5.jpg -> 5.png  (OK 417x417 circle=(cx=414, cy=364, r=200))
[完成] 6.jpg -> 6.png  (OK 416x415 circle=(cx=414, cy=365, r=199))
[完成] 测试_1.jpg -> 测试_1.png  (OK 492x492 circle=(cx=397, cy=421, r=238))

==== 全部完成：成功 7 张，失败 0 张 ====
```

### C —— 排版工具.exe（`排版日志.txt`，337 字节）

```
======== 徽章排版工具 ========
模板: 排版demo.png   输入: 底图\*.png   输出: 已排版\第N页.png

模板: 2480x3508
识别到 11 个槽位
底图数量: 7
共 1 页(每页 11 个槽位)
  已生成 D:\workspace\_koutu_golden\已排版\第1页.png

完成。请打开「已排版」文件夹查看结果。
```

### D —— layout.ps1（`_layout_log.txt`，1234 字节，全文）

```
demo: 2480x3508
detected 18 slots:
  slot center=(474.5,448.5) r=414.0 d=828.0
  slot center=(2017.5,448.5) r=414.0 d=828.0
  slot center=(1247.5,864.5) r=414.0 d=828.0
  slot center=(474.5,1316.5) r=414.0 d=828.0
  slot center=(2013.5,1316.5) r=414.0 d=828.0
  slot center=(1244.5,1753.5) r=414.0 d=828.0
  slot center=(470.5,2189.5) r=414.0 d=828.0
  slot center=(2021.5,2194.5) r=414.0 d=828.0
  slot center=(1246.5,2628.5) r=414.0 d=828.0
  slot center=(2018.5,3065.5) r=414.0 d=828.0
  slot center=(474.5,3067.5) r=414.0 d=828.0
fitted 11 circles
base files: 7
base 1.png: circle center=(207.5,207.5) r=204.0
base 2.png: circle center=(207.5,207.0) r=203.0
base 3.png: circle center=(208.5,208.0) r=204.0
base 4.png: circle center=(208.5,207.5) r=204.0
base 5.png: circle center=(208.5,207.5) r=204.0
base 6.png: circle center=(207.5,207.0) r=203.5
base 测试_1.png: circle center=(245.0,245.0) r=241.5
pages: 1 (11 per page)
  p1 slot# 1 (475,449) <- 1.png
  p1 slot# 2 (2018,449) <- 2.png
  p1 slot# 3 (1248,865) <- 3.png
  p1 slot# 4 (475,1317) <- 4.png
  p1 slot# 5 (2014,1317) <- 5.png
  p1 slot# 6 (1245,1754) <- 6.png
  p1 slot# 7 (471,2190) <- 测试_1.png
  -> 已排版\第1页.png
```

## 产物清单（副本 before→after，共 11 项）

- 数据目录内 8 项（见 `checksums/baseline_products_diff.csv`）：`底图\1.png、2.png、3.png、4.png、5.png、6.png、测试_1.png`、`已排版\第1页.png`
- 根目录 3 个日志（见 `checksums/tree_diff_report.csv`）：`运行日志.txt`、`排版日志.txt`、`_layout_log.txt`

## 备注

- 每步的完整 stdout / stderr / changed_files.csv 在 `logs/steps/<步骤>/`；两侧完整目录清单与差异报告在 `checksums/`。
- 首跑（A1/B1）与自检（S0）的机读记录保存在 `logs/run_steps.jsonl`（退出码字段为空的行即 v1 记录）。
- 本次冻结未运行去水印相关工具（按任务要求：旧输出不作数，留占位）。
