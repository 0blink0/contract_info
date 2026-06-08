param(
  [Parameter(Mandatory = $true)]
  [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Validate version format
if (-not ($Version -match '^\d+\.\d+\.\d+$')) {
  throw "Version must be semver (e.g. 1.2.0). Got: '$Version'"
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "=== Step 1: PyInstaller backend ==="
& (Join-Path $PSScriptRoot "package_backend.ps1") -Platform win-x64 -Version $Version

Write-Host "=== Step 2: Vite frontend (Electron: relative base + hash router) ==="
Push-Location (Join-Path $Root "frontend")
$env:VITE_ELECTRON = '1'
try {
  npm run build
} finally {
  Remove-Item Env:VITE_ELECTRON -ErrorAction SilentlyContinue
}
Pop-Location

Write-Host "=== Step 3: tsc electron main process + stage preload.cjs ==="
Push-Location $Root
npm run build:electron
Pop-Location

Write-Host "=== Step 4: electron-builder (Windows NSIS) ==="
Push-Location $Root
npx electron-builder --win "-c.extraMetadata.version=$Version"
Pop-Location

Write-Host "Build complete. Artifacts in dist/"
