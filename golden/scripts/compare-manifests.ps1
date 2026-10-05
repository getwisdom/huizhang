# compare-manifests.ps1 —— 比对两份 hash-tree.ps1 生成的清单
# 用法:
#   powershell -ExecutionPolicy Bypass -File compare-manifests.ps1 -Before a.csv -After b.csv [-Out diff.csv]
# 退出码: 0 = 完全一致；1 = 存在差异（仅Before / 仅After / 内容不同）。
param(
  [Parameter(Mandatory)][string]$Before,
  [Parameter(Mandatory)][string]$After,
  [string]$Out = ''
)
$a = @{}; Import-Csv -LiteralPath $Before | ForEach-Object { $a[$_.RelPath] = $_.SHA256 }
$b = @{}; Import-Csv -LiteralPath $After  | ForEach-Object { $b[$_.RelPath] = $_.SHA256 }
$diffs = New-Object System.Collections.Generic.List[object]
foreach ($k in $a.Keys) {
  if (-not $b.ContainsKey($k)) { $diffs.Add([pscustomobject]@{ Kind = '仅Before'; RelPath = $k; SHA_Before = $a[$k]; SHA_After = '' }) }
  elseif ($b[$k] -ne $a[$k]) { $diffs.Add([pscustomobject]@{ Kind = '内容不同'; RelPath = $k; SHA_Before = $a[$k]; SHA_After = $b[$k] }) }
}
foreach ($k in $b.Keys) {
  if (-not $a.ContainsKey($k)) { $diffs.Add([pscustomobject]@{ Kind = '仅After'; RelPath = $k; SHA_Before = ''; SHA_After = $b[$k] }) }
}
$dl = @($diffs | Sort-Object RelPath)
Write-Output ('Before 文件数: ' + $a.Count + ' | After 文件数: ' + $b.Count + ' | 差异数: ' + $dl.Count)
foreach ($d in $dl) { Write-Output ('  [' + $d.Kind + '] ' + $d.RelPath) }
if ($Out -ne '') { $dl | Export-Csv -LiteralPath $Out -NoTypeInformation -Encoding UTF8; Write-Output ('差异清单已写入: ' + $Out) }
if ($dl.Count -eq 0) { exit 0 } else { exit 1 }
