# watermark_research —— W3 水印测绘（架构级研究留档）

**状态（已结案·未采用）**：本目录为 W3 去水印研究留档（工程侧已完成测绘定稿、选型、原型与样张，见 `docs/水印研究.md`）；**2026-10-06 使用者决定取消本地去水印（交豆包等外部工具人工处理）**——本目录全部留档、不参与验收。

**有效工具**（重跑方式，输出建议重定向到文件后以 UTF-8 读取）：
- `research4.py`：NCC² 自相关（找点阵基向量）；
- `research5.py`：四角 48×48 纯背景块测绘（自相关 + 按候选基折叠字形）；
- `research6.py`：亚像素周期精定 + 相位优化折叠。
- `research7.py`：7 张统计汇总（间距/幅度/覆盖率，含 13×13 半阶对照）；
- `research8_cross.py`：跨图折叠字形一致性矩阵；
- `research9_proto.py`：去除原型（相位折叠模板扣除，结案留档）。

**过程快照（含已知缺陷，仅作演进留档）**：`research.py`（平坦窗假设不成立）、`research2.py`（分箱越界缺陷）、`research3.py`（广播错误未修）。

**关键结论**（详见 `docs/汇报/08-架构交接.md` §3.3）：
- 底图四角（圆外背景）是最佳观测区：残差 std≈2.0（徽章内部纹理 std≈44，水印被淹没）；
- 点阵几何 ≈ **26px 准正交**（自相关峰 (±26,0)/(0,∓26)，半阶 (±13,0)；亚像素初值 b1=(26.104,0.067)、b2=(0.972,25.995)）；
- 26×26 相位折叠可重建**跨四角一致的重复字形结构**（9216 px、样本/格≈14）。

**运行示例**：

```powershell
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
.\.venv\Scripts\python.exe spike\watermark_research\research5.py 1.png > $env:TEMP\w5.txt 2>&1
Get-Content $env:TEMP\w5.txt -Encoding UTF8
```
