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

Write-Host "=== Step 2: Vite frontend ==="
Push-Location (Join-Path $Root "frontend")
npm run build
Pop-Location

Write-Host "=== Step 3: tsc electron main process ==="
Push-Location $Root
npx tsc -p tsconfig.electron.json
Pop-Location

Write-Host "=== Step 4: electron-builder (Windows NSIS) ==="
Push-Location $Root
npx electron-builder --win "-c.extraMetadata.version=$Version"
Pop-Location

Write-Host "Build complete. Artifacts in dist/"
