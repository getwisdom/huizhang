param(
  [string]$Mode = "slot",
  [string]$Src = "",
  [string]$Out = "",
  [double]$X = 0, [double]$Y = 0, [double]$W = 0, [double]$H = 0,
  [double]$DestX = 0, [double]$DestY = 0, [double]$DestW = 0, [double]$DestH = 0,
  [int]$CanvasW = 1000, [int]$CanvasH = 1000
)
# Dev probe: render GDI+ HighQualityBicubic samples for kernel/phase characterization.
# ASCII-only on purpose (no BOM issues under PowerShell 5.1).
Add-Type -AssemblyName System.Drawing

function New-WhiteCanvas([int]$w, [int]$h) {
  $b = New-Object System.Drawing.Bitmap($w, $h, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g = [System.Drawing.Graphics]::FromImage($b)
  $g.Clear([System.Drawing.Color]::White)
  return @($b, $g)
}

function Setup-G([System.Drawing.Graphics]$g) {
  $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
  $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
}

if ($Mode -eq "slot") {
  $bmp = New-Object System.Drawing.Bitmap($Src)
  $pair = New-WhiteCanvas $CanvasW $CanvasH
  $canvas = $pair[0]; $g = $pair[1]
  Setup-G $g
  $dest = New-Object System.Drawing.RectangleF([float]$DestX, [float]$DestY, [float]$DestW, [float]$DestH)
  $srcR = New-Object System.Drawing.RectangleF([float]$X, [float]$Y, [float]$W, [float]$H)
  $g.DrawImage($bmp, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $canvas.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
  $canvas.Dispose(); $bmp.Dispose()
}
elseif ($Mode -eq "step") {
  $s = New-Object System.Drawing.Bitmap(16, 16, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  for ($yy = 0; $yy -lt 16; $yy++) {
    for ($xx = 0; $xx -lt 16; $xx++) {
      $v = 0; if ($xx -ge 8) { $v = 255 }
      $s.SetPixel($xx, $yy, [System.Drawing.Color]::FromArgb(255, $v, $v, $v))
    }
  }
  $pair = New-WhiteCanvas 160 160
  $d = $pair[0]; $g = $pair[1]
  Setup-G $g
  $dest = New-Object System.Drawing.RectangleF(0.0, 0.0, 160.0, 160.0)
  $srcR = New-Object System.Drawing.RectangleF(0.0, 0.0, 16.0, 16.0)
  $g.DrawImage($s, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $d.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
  $d.Dispose(); $s.Dispose()
}
elseif ($Mode -eq "impulse") {
  $s = New-Object System.Drawing.Bitmap(16, 16, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  for ($yy = 0; $yy -lt 16; $yy++) {
    for ($xx = 0; $xx -lt 16; $xx++) {
      $s.SetPixel($xx, $yy, [System.Drawing.Color]::Black)
    }
  }
  $s.SetPixel(8, 8, [System.Drawing.Color]::White)
  $pair = New-WhiteCanvas 160 160
  $d = $pair[0]; $g = $pair[1]
  Setup-G $g
  $dest = New-Object System.Drawing.RectangleF(0.0, 0.0, 160.0, 160.0)
  $srcR = New-Object System.Drawing.RectangleF(0.0, 0.0, 16.0, 16.0)
  $g.DrawImage($s, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $d.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
  $d.Dispose(); $s.Dispose()
}
elseif ($Mode -eq "ramp") {
  # 源为先横向渐变（0..255 循环）的 16x16 图；用于验证相位与插值方向
  $s = New-Object System.Drawing.Bitmap(16, 16, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $vals = @(0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240)
  for ($yy = 0; $yy -lt 16; $yy++) {
    for ($xx = 0; $xx -lt 16; $xx++) {
      $v = $vals[$xx]
      $s.SetPixel($xx, $yy, [System.Drawing.Color]::FromArgb(255, $v, $v, $v))
    }
  }
  $pair = New-WhiteCanvas 160 160
  $d = $pair[0]; $g = $pair[1]
  Setup-G $g
  $dest = New-Object System.Drawing.RectangleF(0.0, 0.0, 160.0, 160.0)
  $srcR = New-Object System.Drawing.RectangleF(0.0, 0.0, 16.0, 16.0)
  $g.DrawImage($s, $dest, $srcR, [System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $d.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
  $d.Dispose(); $s.Dispose()
}
else {
  Write-Error "unknown mode: $Mode"
  exit 1
}
Write-Output "OK $Mode -> $Out"
