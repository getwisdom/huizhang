# _probe_demo.ps1 —— 排版demo.png 结构探测（开发辅助脚本，可删除）
param(
    [string]$Demo = "排版demo.png",
    [string]$Base = "底图\测试_1.png",
    [int]$Thr = 40,
    [int]$MapCols = 100
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }

function Get-Rgb([string]$path) {
    $b = New-Object System.Drawing.Bitmap($path)
    $w = $b.Width; $h = $b.Height
    $c = New-Object System.Drawing.Bitmap($w, $h, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $g = [System.Drawing.Graphics]::FromImage($c)
    $g.DrawImage($b, 0, 0, $w, $h)
    $g.Dispose(); $b.Dispose()
    $bd = $c.LockBits((New-Object System.Drawing.Rectangle(0, 0, $w, $h)), [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $px = New-Object byte[] ($bd.Stride * $h)
    [System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0, $px, 0, $px.Length)
    $c.UnlockBits($bd)
    $out = New-Object byte[] ($w * $h * 3)
    for ($y = 0; $y -lt $h; $y++) { [Array]::Copy($px, $y * $bd.Stride, $out, $y * $w * 3, $w * 3) }
    $c.Dispose()
    return @{ W = $w; H = $h; Px = $out }
}

function Get-Alpha([string]$path) {
    $b = New-Object System.Drawing.Bitmap($path)
    $w = $b.Width; $h = $b.Height
    $bd = $b.LockBits((New-Object System.Drawing.Rectangle(0, 0, $w, $h)), [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $px = New-Object byte[] ($bd.Stride * $h)
    [System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0, $px, 0, $px.Length)
    $b.UnlockBits($bd); $b.Dispose()
    $out = New-Object byte[] ($w * $h)
    for ($y = 0; $y -lt $h; $y++) { for ($x = 0; $x -lt $w; $x++) { $out[$y * $w + $x] = $px[$y * $bd.Stride + $x * 4 + 3] } }
    return @{ W = $w; H = $h; Px = $out }
}

# 把“命中数数组”聚合成连续区间
function Get-Bands([int[]]$hits, [int]$thr) {
    $list = New-Object System.Collections.ArrayList
    $start = -1
    for ($i = 0; $i -lt $hits.Length; $i++) {
        if ($hits[$i] -gt $thr) {
            if ($start -lt 0) { $start = $i }
        }
        else {
            if ($start -ge 0) {
                $end = $i - 1
                [void]$list.Add(@($start, $end))
                $start = -1
            }
        }
    }
    if ($start -ge 0) { [void]$list.Add(@($start, ($hits.Length - 1))) }
    return $list.ToArray()
}

$basePath = Join-Path $root $Base
if (Test-Path -LiteralPath $basePath) {
    $ba = Get-Alpha $basePath
    $opaque = 0
    $minx = $ba.W; $maxx = -1; $miny = $ba.H; $maxy = -1
    for ($y = 0; $y -lt $ba.H; $y++) {
        for ($x = 0; $x -lt $ba.W; $x++) {
            if ($ba.Px[$y * $ba.W + $x] -gt 16) {
                $opaque++
                if ($x -lt $minx) { $minx = $x }
                if ($x -gt $maxx) { $maxx = $x }
                if ($y -lt $miny) { $miny = $y }
                if ($y -gt $maxy) { $maxy = $y }
            }
        }
    }
    Write-Output ("底图 {0}: {1}x{2}  不透明像素={3} ({4:P1})  包围盒=({5},{6})-({7},{8}) 尺寸={9}x{10}" -f `
            $Base, $ba.W, $ba.H, $opaque, ($opaque / ($ba.W * $ba.H)), $minx, $miny, $maxx, $maxy, ($maxx - $minx + 1), ($maxy - $miny + 1))
    $alphaPath = Join-Path $root "_probe_base_alpha.txt"
    $sb = New-Object System.Text.StringBuilder
    for ($y = 0; $y -lt $ba.H; $y += 8) {
        for ($x = 0; $x -lt $ba.W; $x += 4) { [void]$sb.Append($(if ($ba.Px[$y * $ba.W + $x] -gt 16) { '#' } else { '.' })) }
        [void]$sb.AppendLine()
    }
    Set-Content -LiteralPath $alphaPath -Value $sb.ToString() -Encoding UTF8
    Write-Output "底图 alpha 缩略图(step=4/8) -> _probe_base_alpha.txt"
}

$demoPath = Join-Path $root $Demo
if (-not (Test-Path -LiteralPath $demoPath)) { Write-Output "demo 不存在"; exit }
$d = Get-Rgb $demoPath
Write-Output ("排版demo: {0}x{1}" -f $d.W, $d.H)

$bg = @($d.Px[(2 * $d.W + 2) * 3], $d.Px[(2 * $d.W + 2) * 3 + 1], $d.Px[(2 * $d.W + 2) * 3 + 2])
Write-Output ("背景色 #{0:X2}{1:X2}{2:X2}" -f $bg[0], $bg[1], $bg[2])

$rowHits = New-Object int[] $d.H
$colHits = New-Object int[] $d.W
$rowMinX = New-Object int[] $d.H
$rowMaxX = New-Object int[] $d.H
for ($y = 0; $y -lt $d.H; $y++) { $rowMinX[$y] = -1; $rowMaxX[$y] = -1 }
for ($y = 0; $y -lt $d.H; $y++) {
    $base = $y * $d.W
    for ($x = 0; $x -lt $d.W; $x++) {
        $i = ($base + $x) * 3
        $diff = [Math]::Abs($d.Px[$i] - $bg[0]) + [Math]::Abs($d.Px[$i + 1] - $bg[1]) + [Math]::Abs($d.Px[$i + 2] - $bg[2])
        if ($diff -gt $Thr) {
            $rowHits[$y]++
            $colHits[$x]++
            if ($rowMinX[$y] -lt 0) { $rowMinX[$y] = $x }
            $rowMaxX[$y] = $x
        }
    }
}
Set-Content -LiteralPath (Join-Path $root "_probe_demo_rows.csv") -Value (0..($d.H - 1) | ForEach-Object { "$_,$($rowHits[$_]),$($rowMinX[$_]),$($rowMaxX[$_])" }) -Encoding UTF8
Set-Content -LiteralPath (Join-Path $root "_probe_demo_cols.csv") -Value (0..($d.W - 1) | ForEach-Object { "$_,$($colHits[$_])" }) -Encoding UTF8
Write-Output "行/列命中数 -> _probe_demo_rows.csv / _probe_demo_cols.csv"

$thrRow = [int]($d.W * 0.005)
$rowBands = Get-Bands $rowHits $thrRow
Write-Output ("垂直内容带（阈值 {0} px，共 {1} 条）:" -f $thrRow, $rowBands.Count)
for ($k = 0; $k -lt $rowBands.Count; $k++) {
    $s = $rowBands[$k][0]; $e = $rowBands[$k][1]
    $mn = ($s..$e | ForEach-Object { $rowMinX[$_] } | Where-Object { $_ -ge 0 } | Measure-Object -Minimum).Minimum
    $mx = ($s..$e | ForEach-Object { $rowMaxX[$_] } | Where-Object { $_ -ge 0 } | Measure-Object -Maximum).Maximum
    Write-Output ("  #{0,-3} y {1,5}-{2,5} 高{3,5}   x {4,5}-{5,5} 宽{6,5}" -f ($k + 1), $s, $e, ($e - $s + 1), $mn, $mx, ($mx - $mn + 1))
}

$thrCol = [int]($d.H * 0.005)
$colBands = Get-Bands $colHits $thrCol
Write-Output ("水平内容带（阈值 {0} px，共 {1} 条）:" -f $thrCol, $colBands.Count)
foreach ($b in $colBands) { Write-Output ("  x {0,5}-{1,5} 宽{2,5}" -f $b[0], $b[1], ($b[1] - $b[0] + 1)) }

$step = [int][Math]::Ceiling($d.W / $MapCols)
Write-Output ("--- 整体示意 ASCII (step={0}) ---" -f $step)
$lines = New-Object System.Collections.ArrayList
for ($y = 0; $y -lt $d.H; $y += $step) {
    $line = New-Object System.Text.StringBuilder
    for ($x = 0; $x -lt $d.W; $x += $step) {
        $i = ($y * $d.W + $x) * 3
        $diff = [Math]::Abs($d.Px[$i] - $bg[0]) + [Math]::Abs($d.Px[$i + 1] - $bg[1]) + [Math]::Abs($d.Px[$i + 2] - $bg[2])
        if ($diff -le $Thr) { [void]$line.Append('.') }
        else {
            $r = $d.Px[$i]; $g = $d.Px[$i + 1]; $bl = $d.Px[$i + 2]
            $lum = (0.299 * $r + 0.587 * $g + 0.114 * $bl)
            if ($lum -lt 90) { [void]$line.Append('@') }
            elseif ($lum -lt 170) { [void]$line.Append('o') }
            else { [void]$line.Append('-') }
        }
    }
    [void]$lines.Add(("{0,5} {1}" -f $y, $line.ToString()))
}
Write-Output ($lines -join "`n")
