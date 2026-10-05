param(
  [string]$Mode = "impulse_gray",
  [string]$Out = "",
  [int]$SrcN = 32,
  [double]$Scale = 10.0
)
# GDI+ probe v4: gray-background impulse (reveals negative lobes) / gray step.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$srcW = $SrcN
$srcH = 8
$dstW = [int][Math]::Round($SrcN * $Scale)
$dstH = [int][Math]::Round(8 * $Scale)
$s = [System.Drawing.Bitmap]::new($srcW, $srcH, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($yy = 0; $yy -lt $srcH; $yy++) {
  for ($xx = 0; $xx -lt $srcW; $xx++) {
    $v = 128
    if ($Mode -eq "impulse_gray" -and $xx -eq ($srcW / 2)) { $v = 255 }
    if ($Mode -eq "step_gray" -and $xx -ge ($srcW / 2)) { $v = 255 }
    $s.SetPixel($xx, $yy, [System.Drawing.Color]::FromArgb(255, $v, $v, $v))
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
Write-Output "OK $Mode scale=$Scale -> $Out"
