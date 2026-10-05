# run_step.ps1 —— 「金标准冻结」单步运行器（v2）
# ---------------------------------------------------------------------------
# v2 变更（2026-10-05）：改用 .NET Process 直构启动。
#   原因：PowerShell 5.1 的 Start-Process -PassThru 在带重定向等组合下
#   .ExitCode 会返回空（已用对照组实验证实），改用 .NET 方式后退出码可靠；
#   stdout/stderr 直接按原始字节落盘（CopyToAsync），不做编码猜测。
# v1 用于 A1/B1 首跑，其记录中 exitCode 为空；随后以 v2 重跑 A2/B2 补齐退出码，
#   且产物哈希与首跑一致（详见 golden/runbook.md）。
# ---------------------------------------------------------------------------
# 作用：在副本目录里运行一个旧工具，记录：命令行、用时、退出码、标准输出/错误、
#       本步新增或修改的文件清单、关键日志快照，并把记录追加到 _golden_run\steps.jsonl。
# 用法（在 PowerShell 里调用）：
#   & .\run_step.ps1 -Name A2_badge_exe -FilePath 'D:\workspace\_koutu_golden\徽章抠图.exe' -ArgumentList @('--batch')
#   & .\run_step.ps1 -Name B2_cut_ps1 -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
#       -ArgumentList @('-ExecutionPolicy','Bypass','-File','D:\workspace\_koutu_golden\cut_badge.ps1')
param(
  [Parameter(Mandatory)][string]$Name,
  [Parameter(Mandatory)][string]$FilePath,
  [string[]]$ArgumentList = @(),
  [int]$TimeoutSec = 300,
  [string]$CopyRoot = 'D:\workspace\_koutu_golden',
  [string]$RunDir   = 'D:\workspace\_koutu_golden\_golden_run'
)
$ErrorActionPreference = 'Continue'
$stepDir = Join-Path $RunDir ('steps\' + $Name)
New-Item -ItemType Directory -Force -Path $stepDir | Out-Null
$stdout = Join-Path $stepDir 'stdout.txt'
$stderr = Join-Path $stepDir 'stderr.txt'
$t0 = Get-Date
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$startFailed = ''
$proc = $null
try {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FilePath
  $psi.Arguments = (($ArgumentList | ForEach-Object { if ($_ -match '[\s"]') { '"' + $_ + '"' } else { $_ } }) -join ' ')
  $psi.WorkingDirectory = $CopyRoot
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $proc = [System.Diagnostics.Process]::Start($psi)
} catch {
  $startFailed = $_.Exception.Message
}
$timedOut = $false
$exitCode = $null
if ($null -ne $proc) {
  $fsOut = [System.IO.File]::Create($stdout)
  $fsErr = [System.IO.File]::Create($stderr)
  $tOut = $proc.StandardOutput.BaseStream.CopyToAsync($fsOut)
  $tErr = $proc.StandardError.BaseStream.CopyToAsync($fsErr)
  if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
    $timedOut = $true
    try { $proc.Kill() } catch {}
    try { $proc.WaitForExit(5000) | Out-Null } catch {}
  }
  try { $tOut.Wait(10000) | Out-Null } catch {}
  try { $tErr.Wait(10000) | Out-Null } catch {}
  $fsOut.Dispose()
  $fsErr.Dispose()
  try { if ($proc.HasExited) { $exitCode = $proc.ExitCode } } catch {}
}
$sw.Stop()
$t1 = Get-Date
# —— 本步新增/修改的文件（按修改时间，排除 _golden_run）——
# 说明：mtime 严格 >= 本步启动时刻；不使用模糊窗口，避免把紧邻上一步的写盘误记到本步。
$cutUtc = $t0.ToUniversalTime()
$changed = @()
foreach ($f in @(Get-ChildItem -LiteralPath $CopyRoot -Recurse -File -Force -ErrorAction SilentlyContinue)) {
  if ($f.FullName -notlike ($RunDir + '\*') -and $f.LastWriteTimeUtc -ge $cutUtc) {
    $changed += [pscustomobject]@{ RelPath = $f.FullName.Substring($CopyRoot.Length + 1); Length = $f.Length; LastWriteTimeUtc = $f.LastWriteTimeUtc.ToString('o') }
  }
}
$changed = @($changed | Sort-Object RelPath)
$changed | Export-Csv -LiteralPath (Join-Path $stepDir 'changed_files.csv') -NoTypeInformation -Encoding UTF8
# —— 关键日志快照（运行日志.txt / 排版日志.txt / _layout_log.txt）——
$logSnaps = @()
foreach ($lg in @('运行日志.txt','排版日志.txt','_layout_log.txt')) {
  $src = Join-Path $CopyRoot $lg
  if (Test-Path -LiteralPath $src) {
    $it = Get-Item -LiteralPath $src
    if ($it.LastWriteTimeUtc -ge $cutUtc) {
      Copy-Item -LiteralPath $src -Destination (Join-Path $stepDir $lg) -Force
      $logSnaps += ($lg + ' | 本步写入 | ' + $it.Length + ' bytes')
    } else {
      $logSnaps += ($lg + ' | 未变(沿用旧文件) | ' + $it.Length + ' bytes')
    }
  } else {
    $logSnaps += ($lg + ' | 不存在')
  }
}
$rec = [pscustomobject]@{
  runnerVersion = 'v2'
  name = $Name
  file = $FilePath
  args = ($ArgumentList -join ' ')
  workDir = $CopyRoot
  startUtc = $t0.ToUniversalTime().ToString('o')
  endUtc = $t1.ToUniversalTime().ToString('o')
  durationSec = [math]::Round($sw.Elapsed.TotalSeconds, 2)
  exitCode = $exitCode
  timedOut = $timedOut
  startFailed = $startFailed
  changedCount = $changed.Count
  logs = $logSnaps
}
$line = ($rec | ConvertTo-Json -Compress)
[System.IO.File]::AppendAllText((Join-Path $RunDir 'steps.jsonl'), $line + "`r`n", [System.Text.UTF8Encoding]::new($false))
Write-Output ('STEP=' + $Name + ' | DURATION_S=' + $rec.durationSec + ' | EXIT=' + $(if ($null -eq $exitCode) { 'NULL' } else { [string]$exitCode }) + ' | TIMEOUT=' + $timedOut + ' | CHANGED=' + $changed.Count)
if ($startFailed -ne '') { Write-Output ('  START_FAILED: ' + $startFailed) }
foreach ($s in $logSnaps) { Write-Output ('  LOG: ' + $s) }
Write-Output ('  STDOUT_BYTES=' + (Get-Item -LiteralPath $stdout).Length + ' | STDERR_BYTES=' + (Get-Item -LiteralPath $stderr).Length)
