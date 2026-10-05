# layout_calibration —— W2 合成校准过程留档

这些脚本是 W2 校准「排版合成须复现 GDI+ `HighQualityBicubic` + `SourceOver`」时用的
黑盒探针 / 拟合 / 诊断脚本（**过程快照**）。

| 脚本 | 用途 |
| --- | --- |
| `_gdiplus_probe.ps1` / `_gdiplus_probe2.ps1` / `_gdiplus_probe3.ps1` / `_gdiplus_probe4.ps1` | .NET 探针：阶跃 / 黑底脉冲 / 平坦场 / 灰底脉冲（揭示负瓣） |
| `_gdiplus_fullpage.ps1` + `_fullpage_check.py` | 由 JSON 作业重放整页 GDI+ 绘制；三方对照（.NET vs golden vs 我们） |
| `_fit_kernel.py` ~ `_fit_kernel5.py` | 核家族拟合（最终：`mitchell(B=0.25,C=0.875) ⊛ box(0.75)`，逐相 Σ=1） |
| `_calibration_layout.py` / `_calibration_sweep.py` / `_tune_page.py` | 相位 / 参数 / 页面级小网格搜索 |
| `_diag_slots.py` / `_diff_inspect.py` / `_shift_test.py` / `_crescent_inspect.py` / `_ascii_view.py` / `_slot1_check.py` / `_flat_check.py` / `_probe_analyze.py` / `_probe_analyze2.py` | 差异分布 / 相位 / 平坦场 / 单槽深度诊断 |

**运行注意**：
- 探针脚本依赖本机 .NET Framework `System.Drawing`（PowerShell 5.1）与仓库 `.venv`；
- 部分脚本内部引用当时演进中的接口（例如 `layout._render_slot_patch` 的旧返回签名）与
  按 `tests/` 位置推导的 `REPO` 路径，重跑前需按当前接口/路径微调；
- 校准结论与原始数字已固化在 `docs/汇报/07-W2-排版内核.md` 与 `koutu/core/layout.py`
  的 `GDI_B/GDI_C/GDI_BOX`；**日常验证请使用 `pytest tests -q`，不要重跑本目录脚本。**
