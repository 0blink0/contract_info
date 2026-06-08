param(
  [Parameter(Mandatory = $true)]
  [string]$BackendExePath,
  [Parameter(Mandatory = $true)]
  [string]$DataDir,
  [Parameter(Mandatory = $true)]
  [string]$GoldenDocx,
  [string]$BaseUrl = "http://127.0.0.1:8765",
  [int]$StartupTimeoutSec = 45,
  [int]$PipelineTimeoutSec = 240,
  [string]$ApiKey = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host ("[SMOKE] " + $Message)
}

function Fail-Smoke {
  param([string]$Message)
  Write-Error $Message
  exit 1
}

function Invoke-Api {
  param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("GET", "POST")]
    [string]$Method,
    [Parameter(Mandatory = $true)]
    [string]$Uri,
    [hashtable]$Headers = @{},
    [string]$InFile = "",
    [string]$OutFile = ""
  )

  if ($OutFile) {
    if ($Method -eq "GET") {
      Invoke-WebRequest -Method Get -Uri $Uri -Headers $Headers -OutFile $OutFile | Out-Null
      return $null
    }
    throw "OutFile is supported only for GET"
  }

  if ($InFile) {
    # PowerShell 5.1 does not support Invoke-RestMethod -Form; use curl multipart upload.
    $curlArgs = @("-sS", "-X", "POST")
    foreach ($k in $Headers.Keys) {
      $curlArgs += @("-H", ("{0}: {1}" -f $k, $Headers[$k]))
    }
    $curlArgs += @("-F", ("file=@{0}" -f $InFile), $Uri)
    $resp = & curl.exe @curlArgs
    if (-not $resp) {
      throw "Upload request returned empty response"
    }
    return ($resp | ConvertFrom-Json)
  }

  return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers
}

if (-not (Test-Path $BackendExePath)) {
  Fail-Smoke "Backend exe not found: $BackendExePath"
}
if (-not (Test-Path $GoldenDocx)) {
  Fail-Smoke "Golden docx not found: $GoldenDocx"
}

$resolvedDataDir = [System.IO.Path]::GetFullPath($DataDir)
$resolvedExe = (Resolve-Path $BackendExePath).Path
$exeDir = Split-Path -Parent $resolvedExe
$backendRoot = Split-Path -Parent $exeDir

New-Item -ItemType Directory -Path $resolvedDataDir -Force | Out-Null
$logPath = Join-Path $resolvedDataDir "smoke-backend.log"
$errLogPath = Join-Path $resolvedDataDir "smoke-backend.err.log"
$downloadDir = Join-Path $resolvedDataDir "downloads"
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null

$env:CTRX_DATA_DIR = $resolvedDataDir
$env:CTRX_PORT = ([uri]$BaseUrl).Port.ToString()
if ($ApiKey) {
  $env:API_KEY = $ApiKey
}

$headers = @{}
if ($ApiKey) {
  $headers["X-API-Key"] = $ApiKey
}

$backendProc = $null
try {
  Write-Step "Starting backend: $resolvedExe"
  $backendProc = Start-Process -FilePath $resolvedExe -PassThru -RedirectStandardOutput $logPath -RedirectStandardError $errLogPath
  Start-Sleep -Seconds 1
  if ($backendProc.HasExited) {
    Fail-Smoke "Backend exited early. See log: $logPath"
  }

  $healthOk = $false
  $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $health = Invoke-Api -Method GET -Uri "$BaseUrl/api/v1/health" -Headers $headers
      if ($health.status -eq "ok") {
        $healthOk = $true
        break
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }
  if (-not $healthOk) {
    Fail-Smoke "Health check failed within ${StartupTimeoutSec}s. See log: $logPath"
  }
  Write-Step "Health check passed"

  Write-Step "Uploading golden file"
  $upload = Invoke-Api -Method POST -Uri "$BaseUrl/api/v1/upload" -Headers $headers -InFile $GoldenDocx
  $jobId = "$($upload.job_id)"
  if (-not $jobId) {
    Fail-Smoke "Upload did not return job_id"
  }
  Write-Step "Upload passed, job_id=$jobId"

  Write-Step "Triggering extraction/export pipeline"
  $null = Invoke-Api -Method POST -Uri "$BaseUrl/api/v1/jobs/$jobId/run" -Headers $headers

  $exported = $false
  $pipelineDeadline = (Get-Date).AddSeconds($PipelineTimeoutSec)
  while ((Get-Date) -lt $pipelineDeadline) {
    Start-Sleep -Seconds 2
    try {
      $job = Invoke-Api -Method GET -Uri "$BaseUrl/api/v1/jobs/$jobId" -Headers $headers
      $status = "$($job.status)"
      if ($status -eq "exported") {
        $exported = $true
        break
      }
      if ($status -match "failed") {
        Fail-Smoke "Pipeline failed with status=$status"
      }
    } catch {
      # transient read errors while server is warm
    }
  }
  if (-not $exported) {
    Fail-Smoke "Pipeline did not reach exported within ${PipelineTimeoutSec}s"
  }
  Write-Step "Extraction/export passed"

  Write-Step "Downloading product-elements workbook"
  $downloadPath = Join-Path $downloadDir "product_elements.xlsx"
  Invoke-Api -Method GET -Uri "$BaseUrl/api/v1/jobs/$jobId/download/product-elements" -Headers $headers -OutFile $downloadPath
  if (-not (Test-Path $downloadPath)) {
    Fail-Smoke "Download file not found after request: $downloadPath"
  }
  Write-Step "Download passed"

  Write-Step "Verifying CTRX_DATA_DIR isolation"
  $expectedDb = Join-Path $resolvedDataDir "ctrx.db"
  if (-not (Test-Path $expectedDb)) {
    Fail-Smoke "Expected sqlite db not found in CTRX_DATA_DIR: $expectedDb"
  }

  $installWrites = @()
  foreach ($name in @("ctrx.db", "uploads", "exports")) {
    $candidate = Join-Path $backendRoot $name
    if (Test-Path $candidate) {
      $installWrites += $candidate
    }
  }
  if ($installWrites.Count -gt 0) {
    Fail-Smoke ("Detected runtime writes in install directory: " + ($installWrites -join ", "))
  }
  Write-Step "CTRX_DATA_DIR isolation passed"

  Write-Host "PASS: smoke chain health->upload->extract->download completed"
  exit 0
} catch {
  Fail-Smoke ("Smoke failed: " + $_.Exception.Message)
} finally {
  if ($backendProc -and -not $backendProc.HasExited) {
    try {
      Stop-Process -Id $backendProc.Id -Force
    } catch {
      # no-op
    }
  }
}
