# scan_watermark.ps1 - 综合扫描：高亮(黄/橙色块)、网格(周期暗线)、文字
param([string]$JpgPath = "原图\测试_1.jpg", [string]$PngPath = "底图\测试_1.png")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function New-Img([string]$path) {
    $bmp = New-Object System.Drawing.Bitmap($path)
    return $bmp
}

$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }
$jpg = New-Img (Join-Path $root $JpgPath)
$w = $jpg.Width; $h = $jpg.Height

# ---------- 1) 高亮扫描：饱和暖色像素 (黄/橙/红/绿高亮笔) ----------
$bmpData = $jpg.LockBits((New-Object System.Drawing.Rectangle(0,0,$w,$h)), [System.Drawing.Imaging.ImageLockMode]::ReadOnly, $jpg.PixelFormat)
$stride = $bmpData.Stride
$bytes = New-Object byte[] ($stride * $h)
[System.Runtime.InteropServices.Marshal]::Copy($bmpData.Scan0, $bytes, 0, $bytes.Length)
$jpg.UnlockBits($bmpData)
$bpp = [System.Drawing.Image]::GetPixelFormatSize($jpg.PixelFormat) / 8

$yellow = @{}; $orange = @{}; $green = @{}
for ($y=0; $y -lt $h; $y++) {
  for ($x=0; $x -lt $w; $x++) {
    $i = $y*$stride + $x*$bpp
    $b = $bytes[$i]; $g = $bytes[$i+1]; $r = $bytes[$i+2]
    if ($r -gt 190 -and $g -gt 140 -and $b -lt 140 -and ($r-$b) -gt 90) { $yellow["$x,$y"] = 1 }
    elseif ($r -gt 200 -and $g -gt 90 -and $g -lt 170 -and $b -lt 110 -and ($r-$b) -gt 110) { $orange["$x,$y"] = 1 }
    elseif ($g -gt 150 -and $g -gt ($r+30) -and $g -gt ($b+30) -and $r -lt 200) { $green["$x,$y"] = 1 }
  }
}
function Report-Clusters($map, [string]$name) {
    if ($map.Count -eq 0) { Write-Output ("$name : 0 像素"); return }
    # 简单 8x8 分桶聚类
    $cells = @{}
    foreach ($k in $map.Keys) {
        $p = $k -split ","; $cx = [int](([int]$p[0])/8); $cy = [int](([int]$p[1])/8)
        $ck = "$cx,$cy"
        if ($cells.ContainsKey($ck)) { $cells[$ck]++ } else { $cells[$ck] = 1 }
    }
    $big = @($cells.GetEnumerator() | Where-Object { $_.Value -ge 20 } | Sort-Object Value -Descending)
    Write-Output ("$name : 共 {0} 像素, 大块 {1} 个:" -f $map.Count, $big.Count)
    foreach ($c in $big) {
        $p = $c.Key -split ","
        Write-Output ("  x={0}..{1} y={2}..{3}  ~{4}px" -f ([int]$p[0]*8), ([int]$p[0]*8+8), ([int]$p[1]*8), ([int]$p[1]*8+8), $c.Value)
    }
}
Report-Clusters $yellow "黄色高亮"
Report-Clusters $orange "橙色高亮"
Report-Clusters $green  "绿色高亮"

# ---------- 2) 网格扫描：找规律出现的横向/纵向暗线 ----------
# 在白/浅蓝背景区域取样：先对每行统计"暗像素"(lum<235)数量，再找暗像素数突增的行
$darkRows = New-Object int[] $h
$darkCols = New-Object int[] $w
for ($y=0; $y -lt $h; $y++) {
  $cnt=0
  for ($x=0; $x -lt $w; $x+=1) {
    $i = $y*$stride + $x*$bpp
    $lum = 0.299*$bytes[$i+2] + 0.587*$bytes[$i+1] + 0.114*$bytes[$i]
    if ($lum -lt 235) { $cnt++ }
  }
  $darkRows[$y] = $cnt
}
for ($x=0; $x -lt $w; $x++) {
  $cnt=0
  for ($y=0; $y -lt $h; $y+=1) {
    $i = $y*$stride + $x*$bpp
    $lum = 0.299*$bytes[$i+2] + 0.587*$bytes[$i+1] + 0.114*$bytes[$i]
    if ($lum -lt 235) { $cnt++ }
  }
  $darkCols[$x] = $cnt
}
Write-Output "--- 行暗像素数 >600 的行(疑似横线/文字行) ---"
for ($y=0; $y -lt $h; $y++) { if ($darkRows[$y] -gt 600) { Write-Output ("y={0} dark={1}" -f $y, $darkRows[$y]) } }
Write-Output "--- 列暗像素数 >500 的列(疑似竖线/文字列) ---"
for ($x=0; $x -lt $w; $x++) { if ($darkCols[$x] -gt 500) { Write-Output ("x={0} dark={1}" -f $x, $darkCols[$x]) } }

$jpg.Dispose()
