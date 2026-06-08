param(
  [Parameter(Mandatory = $true)]
  [string]$Platform,
  [Parameter(Mandatory = $true)]
  [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistDir = Join-Path $Root "dist/ctrx-backend"
$ResourcesDir = Join-Path $Root "electron/resources"
$ManifestPath = Join-Path $ResourcesDir ".backend-manifest.json"
$TargetName = "ctrx-backend-$Platform-v$Version"
$TargetDir = Join-Path $ResourcesDir $TargetName

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller not found. Run: pip install pyinstaller"
}

python -m PyInstaller (Join-Path $Root "ctrx_backend.spec") --noconfirm --clean --log-level WARN

if (-not (Test-Path $DistDir)) {
  throw "Expected pyinstaller output not found: $DistDir"
}

New-Item -ItemType Directory -Path $ResourcesDir -Force | Out-Null
if (Test-Path $TargetDir) {
  Remove-Item -Path $TargetDir -Recurse -Force
}
Copy-Item -Path $DistDir -Destination $TargetDir -Recurse -Force

$Now = (Get-Date).ToUniversalTime().ToString("o")
$Manifest = @{
  current = @{
    platform = $Platform
    version = $Version
    builtAt = $Now
    path = $TargetName
  }
  previous = $null
}

if (Test-Path $ManifestPath) {
  $Existing = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
  if ($Existing.current -and $Existing.current.platform -eq $Platform -and $Existing.current.path -ne $TargetName) {
    $Manifest.previous = $Existing.current
  } elseif ($Existing.previous -and $Existing.previous.platform -eq $Platform) {
    $Manifest.previous = $Existing.previous
  }
}

# Keep only current and previous generation for this platform.
$Keep = @($Manifest.current.path)
if ($Manifest.previous) {
  $Keep += $Manifest.previous.path
}
Get-ChildItem -Path $ResourcesDir -Directory -Filter "ctrx-backend-$Platform-v*" | ForEach-Object {
  if ($Keep -notcontains $_.Name) {
    Remove-Item -Path $_.FullName -Recurse -Force
  }
}

$json = $Manifest | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($ManifestPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "Packaged backend to $TargetDir"
