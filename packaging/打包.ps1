# koutu 打包脚本 —— PyInstaller 单目录绿色包（--onedir --windowed）
#
# 用法（仓库任意位置均可执行）：
#   powershell -ExecutionPolicy Bypass -File packaging\打包.ps1
# 产物：
#   dist\koutu\ = koutu.exe + _internal\ + 排版demo.png + 使用说明.txt
#   （整目录一起拷贝分发；dist\ / build\ 不入库）
#
# 依赖：仓库 .venv（requirements.txt 锁定）；BOM 由仓库约定保证（UTF-8 带 BOM）。
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot          # 仓库根（packaging\ 的上一级）
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "找不到解释器 $py（请先准备仓库 .venv）" }

Push-Location $root
try {
    Write-Host "[1/3] PyInstaller 构建（packaging\koutu.spec）..."
    & $py -m PyInstaller --noconfirm --clean "packaging\koutu.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败（退出码 $LASTEXITCODE）" }

    Write-Host "[2/3] 拷贝随包资源到 exe 同级..."
    Copy-Item "排版demo.png" "dist\koutu\排版demo.png" -Force
    Copy-Item "使用说明.txt" "dist\koutu\使用说明.txt" -Force

    Write-Host "[3/3] 汇总产物..."
    $files = Get-ChildItem "dist\koutu" -Recurse -File
    $sum = ($files | Measure-Object -Property Length -Sum).Sum
    $mb = [math]::Round($sum / 1MB, 1)
    Write-Host ("完成：dist\koutu\ = {0} 个文件 / {1} MB" -f $files.Count, $mb)
} finally {
    Pop-Location
}
