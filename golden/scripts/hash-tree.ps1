# hash-tree.ps1 —— 计算目录内容 SHA256 清单（金标准冻结 / 验收复用）
# 用法:
#   powershell -ExecutionPolicy Bypass -File hash-tree.ps1 -Base D:\workspace\koutu -Out D:\out.csv -Include 原图,底图,已排版
# 说明: -Include 为相对 -Base 的子目录/文件清单，留空则扫描整个 Base。
#       输出 CSV 列：RelPath, Length, LastWriteTimeUtc, SHA256（按 RelPath 排序）。
param(
  [Parameter(Mandatory)][string]$Base,
  [Parameter(Mandatory)][string]$Out,
  [string[]]$Include = @()
)
# 兼容命令行逗号写法：-Include 原图,底图 在 -File 调用时会被绑定为单个字符串
if ($Include.Count -eq 1 -and $Include[0].Contains(',')) { $Include = @($Include[0] -split ',') }
$baseFull = [System.IO.Path]::GetFullPath($Base).TrimEnd('\')
$targets = @()
if ($Include.Count -gt 0) {
  foreach ($rel in $Include) { $targets += (Join-Path $baseFull $rel) }
} else {
  $targets += $baseFull
}
$rows = New-Object System.Collections.Generic.List[object]
foreach ($t in $targets) {
  if (-not (Test-Path -LiteralPath $t)) {
    $rel = $t.Substring($baseFull.Length + 1)
    $rows.Add([pscustomobject]@{ RelPath = ($rel + '\<MISSING>'); Length = -1; LastWriteTimeUtc = ''; SHA256 = '' })
    continue
  }
  $items = @()
  if ((Get-Item -LiteralPath $t).PSIsContainer) { $items = @(Get-ChildItem -LiteralPath $t -Recurse -File -Force -ErrorAction SilentlyContinue) }
  else { $items = @(Get-Item -LiteralPath $t) }
  foreach ($f in $items) {
    $rows.Add([pscustomobject]@{ RelPath = $f.FullName.Substring($baseFull.Length + 1); Length = $f.Length; LastWriteTimeUtc = $f.LastWriteTimeUtc.ToString('o'); SHA256 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash })
  }
}
$sorted = @($rows | Sort-Object RelPath)
$sorted | Export-Csv -LiteralPath $Out -NoTypeInformation -Encoding UTF8
Write-Output ('清单已写入: ' + $Out)
Write-Output ('文件数: ' + $sorted.Count)
