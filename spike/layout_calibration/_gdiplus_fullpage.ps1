param(
  [Parameter(Mandatory = $true)][string]$Ops
)
# Full-page GDI+ render driven by a JSON job file (schema v1).
# Job: { "canvasW": int, "canvasH": int, "out": "path.png",
#        "draws": [ {file, sx, sy, sw, sh, dx, dy, dw, dh}, ... ] }
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$job = Get-Content -LiteralPath $Ops -Raw -Encoding UTF8 | ConvertFrom-Json
$canvasW = [int]$job.canvasW
$canvasH = [int]$job.canvasH
$out = [string]$job.out
$canvas = [System.Drawing.Bitmap]::new($canvasW, $canvasH, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($canvas)
$g.Clear([System.Drawing.Color]::White)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
foreach ($d in $job.draws) {
  $bmp = [System.Drawing.Bitmap]::new([string]$d.file)
  $dest = [System.Drawing.RectangleF]::new([float]$d.dx, [float]$d.dy, [float]$d.dw, [float]$d.dh)
  $srcR = [System.Drawing.RectangleF]::new([float]$d.sx, [float]$d.sy, [float]$d.sw, [float]$d.sh)
  $g.DrawImage($bmp, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
  $bmp.Dispose()
}
$g.Dispose()
$canvas.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$canvas.Dispose()
Write-Output "OK fullpage -> $out"
