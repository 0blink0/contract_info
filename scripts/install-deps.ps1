# 使用清华 PyPI 镜像安装依赖
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$Pip = Join-Path $Root ".venv\Scripts\pip.exe"
$Mirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
& $Pip install -i $Mirror --trusted-host pypi.tuna.tsinghua.edu.cn -r (Join-Path $Root "requirements.txt")

Write-Host "Done. Activate: .\.venv\Scripts\Activate.ps1"
