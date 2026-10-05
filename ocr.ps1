# ocr.ps1 - Windows 内置 OCR 读取图片文字（含位置框）
param([string]$ImagePath = "原图\测试_1.jpg")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.RandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }
$path = Join-Path $root $ImagePath
if (-not (Test-Path $path)) { Write-Output "not found: $path"; exit 1 }

$file    = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
$stream  = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bitmap  = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$stream.Dispose()

Write-Output ("image: {0} x {1}  format: {2}" -f $decoder.PixelWidth, $decoder.PixelHeight, $bitmap.BitmapPixelFormat)

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($engine -eq $null) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language "zh-CN")) }
if ($engine -eq $null) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage((New-Object Windows.Globalization.Language "en-US")) }
if ($engine -eq $null) { Write-Output "no OCR engine"; exit 1 }
Write-Output ("ocr language: {0}" -f $engine.RecognizerLanguage.LanguageTag)
Write-Output ""

$result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
$i = 0
foreach ($line in $result.Lines) {
    $x0 = 99999; $y0 = 99999; $x1 = -1; $y1 = -1
    foreach ($w in $line.Words) {
        $r = $w.BoundingRect
        if ($r.X -lt $x0) { $x0 = $r.X }; if ($r.Y -lt $y0) { $y0 = $r.Y }
        if (($r.X + $r.Width) -gt $x1) { $x1 = $r.X + $r.Width }
        if (($r.Y + $r.Height) -gt $y1) { $y1 = $r.Y + $r.Height }
    }
    $i++
    Write-Output ("[{0,2}] box=({1},{2})-({3},{4})  {5}" -f $i, [int]$x0, [int]$y0, [int]$x1, [int]$y1, $line.Text)
}
