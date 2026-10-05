param(
  [string]$Mode = "flat",
  [string]$Out = "",
  [int]$SrcN = 32,
  [double]$Scale = 10.0,
  [int]$Gray = 100
)
# GDI+ flat-field probe: constant gray source scaled up; per-phase gain check.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$srcW = $SrcN
$srcH = 8
$dstW = [int][Math]::Round($SrcN * $Scale)
$dstH = [int][Math]::Round(8 * $Scale)
$s = [System.Drawing.Bitmap]::new($srcW, $srcH, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($yy = 0; $yy -lt $srcH; $yy++) {
  for ($xx = 0; $xx -lt $srcW; $xx++) {
    $s.SetPixel($xx, $yy, [System.Drawing.Color]::FromArgb(255, $Gray, $Gray, $Gray))
  }
}
$d = [System.Drawing.Bitmap]::new($dstW, $dstH, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($d)
$g.Clear([System.Drawing.Color]::White)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
$dest = [System.Drawing.RectangleF]::new(0.0, 0.0, [float]$dstW, [float]$dstH)
$srcR = [System.Drawing.RectangleF]::new(0.0, 0.0, [float]$srcW, [float]$srcH)
$g.DrawImage($s, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
$g.Dispose()
$d.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$d.Dispose()
$s.Dispose()
Write-Output "OK flat gray=$Gray scale=$Scale -> $Out"
