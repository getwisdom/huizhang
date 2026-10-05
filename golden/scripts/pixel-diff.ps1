# pixel-diff.ps1 —— 像素级对照（金标准冻结 / 验收复用）
# 用法:
#   powershell -ExecutionPolicy Bypass -File pixel-diff.ps1 -Old <目录A> -New <目录B> -Paths 底图\1.png,已排版\第1页.png
# 说明: 对每个相对路径，比较 <目录A>\path 与 <目录B>\path（两张同尺寸 PNG）：
#   输出 尺寸、不透明像素数（两边及占全图百分比）、alpha 差 > 8 的像素数及占比、
#   最大 alpha 差、双方都可见(al>8)但 RGB 任一通道差 > 8 的像素数及占比。
#   内联 C# 计算（Add-Type 编译），避免 PowerShell 逐像素循环过慢。
param(
  [Parameter(Mandatory)][string]$Old,
  [Parameter(Mandatory)][string]$New,
  [Parameter(Mandatory)][string[]]$Paths
)
# 兼容命令行逗号写法：-Paths 底图\1.png,底图\2.png 在 -File 调用时会被绑定为单个字符串
if ($Paths.Count -eq 1 -and $Paths[0].Contains(',')) { $Paths = @($Paths[0] -split ',') }
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class KunPixelDiff {
  public static string Compare(string pathA, string pathB) {
    using (var a = new Bitmap(pathA)) using (var b = new Bitmap(pathB)) {
      if (a.Width != b.Width || a.Height != b.Height)
        return string.Format("SIZE_DIFF {0}x{1} vs {2}x{3}", a.Width, a.Height, b.Width, b.Height);
      int w = a.Width, h = a.Height;
      var rect = new Rectangle(0, 0, w, h);
      var da = a.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
      var db = b.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
      int sA = da.Stride, sB = db.Stride;
      int lenA = sA * h, lenB = sB * h;
      var ba = new byte[lenA]; var bb = new byte[lenB];
      Marshal.Copy(da.Scan0, ba, 0, lenA);
      Marshal.Copy(db.Scan0, bb, 0, lenB);
      a.UnlockBits(da); b.UnlockBits(db);
      long opaqueA = 0, opaqueB = 0, alphaDiffGt8 = 0, rgbDiffGt8 = 0;
      int maxAlphaDiff = 0;
      if (sA == sB) {
        for (int i = 0; i < lenA; i += 4) {
          byte alA = ba[i + 3], alB = bb[i + 3];
          if (alA > 0) opaqueA++;
          if (alB > 0) opaqueB++;
          int d = alA - alB; if (d < 0) d = -d;
          if (d > 8) alphaDiffGt8++;
          if (d > maxAlphaDiff) maxAlphaDiff = d;
          if (alA > 8 && alB > 8) {
            int dr = ba[i] - bb[i]; if (dr < 0) dr = -dr;
            int dg = ba[i+1] - bb[i+1]; if (dg < 0) dg = -dg;
            int dbl = ba[i+2] - bb[i+2]; if (dbl < 0) dbl = -dbl;
            if (dr > 8 || dg > 8 || dbl > 8) rgbDiffGt8++;
          }
        }
      }
      double total = (double)w * h;
      return string.Format("OK {0}x{1} | opaqueA={2}({3:F3}%) | opaqueB={4}({5:F3}%) | alphaDiff>8={6}({7:F4}%) | maxAlphaDiff={8} | rgbDiff>8={9}({10:F4}%)",
        w, h, opaqueA, opaqueA*100.0/total, opaqueB, opaqueB*100.0/total, alphaDiffGt8, alphaDiffGt8*100.0/total, maxAlphaDiff, rgbDiffGt8, rgbDiffGt8*100.0/total);
    }
  }
}
'@
if (-not ('KunPixelDiff' -as [type])) {
  Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing
}
foreach ($rel in $Paths) {
  $pa = Join-Path $Old $rel
  $pb = Join-Path $New $rel
  if (-not (Test-Path -LiteralPath $pa)) { Write-Output ($rel + ' | 缺少 Old 文件'); continue }
  if (-not (Test-Path -LiteralPath $pb)) { Write-Output ($rel + ' | 缺少 New 文件'); continue }
  try {
    Write-Output ($rel + ' | ' + [KunPixelDiff]::Compare($pa, $pb))
  } catch {
    Write-Output ($rel + ' | ERROR: ' + $_.Exception.Message)
  }
}
