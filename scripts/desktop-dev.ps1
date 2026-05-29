# Local desktop dev: one command from repo root (contract_info/).
#   npm run desktop:dev        — build electron + frontend, then launch
#   npm run desktop:dev:quick  — skip rebuild when dist already exists
#   npm run desktop:dev:watch  — Vite HMR + Electron (frontend/UI iteration)
param(
    [switch]$Quick,
    [switch]$Watch
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $Root

function Test-BackendBundle {
    Test-Path 'electron\resources\ctrx-backend-win-x64-v1.2.0\ctrx-backend.exe' -or
        (Test-Path 'electron\resources\.backend-manifest.json')
}

function Ensure-BackendBundle {
    if (Test-BackendBundle) { return }
    Write-Host '=== Backend bundle missing — packaging PyInstaller (first time / after backend changes) ==='
    & (Join-Path $PSScriptRoot 'package_backend.ps1') -Platform win-x64 -Version 1.2.0
}

function Build-ElectronMain {
    Write-Host '=== Electron main (tsc + preload.cjs) ==='
    npm run build:electron
}

function Build-FrontendProduction {
    Write-Host '=== Frontend production build (Electron file://) ==='
    $env:VITE_ELECTRON = '1'
    try {
        npm run build --prefix frontend
    } finally {
        Remove-Item Env:VITE_ELECTRON -ErrorAction SilentlyContinue
    }
}

function Wait-HttpPort {
    param([int]$Port, [int]$TimeoutSec = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -ge 200) { return }
        } catch {
            Start-Sleep -Milliseconds 400
        }
    }
    throw "Timed out waiting for http://127.0.0.1:$Port (Vite dev server)"
}

function Start-ViteDev {
    $env:VITE_ELECTRON = '1'
    $proc = Start-Process -FilePath 'npm.cmd' -ArgumentList @('run', 'dev', '--prefix', 'frontend') `
        -WorkingDirectory $Root -PassThru -WindowStyle Hidden
    try {
        Wait-HttpPort -Port 5173
    } catch {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        throw
    }
    return $proc
}

$electronMain = Join-Path $Root 'dist\electron\main.js'
$frontendIndex = Join-Path $Root 'frontend\dist\index.html'

if ($Quick) {
    Write-Host '=== Quick mode: skip rebuild when artifacts exist ==='
    if (-not (Test-Path $electronMain)) { Build-ElectronMain }
    if (-not $Watch -and -not (Test-Path $frontendIndex)) { Build-FrontendProduction }
} else {
    Build-ElectronMain
    if (-not $Watch) { Build-FrontendProduction }
}

Ensure-BackendBundle

$viteProc = $null
try {
    if ($Watch) {
        Write-Host '=== Vite dev server (HMR) + Electron ==='
        $viteProc = Start-ViteDev
        $env:ELECTRON_RENDERER_URL = 'http://127.0.0.1:5173'
    } else {
        Remove-Item Env:ELECTRON_RENDERER_URL -ErrorAction SilentlyContinue
    }

    Write-Host '=== Starting Electron (close the window to stop) ==='
    npx electron .
} finally {
    Remove-Item Env:ELECTRON_RENDERER_URL -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_ELECTRON -ErrorAction SilentlyContinue
    if ($viteProc -and -not $viteProc.HasExited) {
        Stop-Process -Id $viteProc.Id -Force -ErrorAction SilentlyContinue
    }
}
