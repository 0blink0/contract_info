# Push via SSH on port 443 (when github.com:443 HTTPS is blocked)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
if (-not (Test-Path "$env:USERPROFILE\.ssh\id_ed25519")) {
    Write-Error "Missing ~/.ssh/id_ed25519 — run setup from README or ask agent."
}
ssh -T git@github.com 2>&1 | Out-Null
if ($LASTEXITCODE -ne 1 -and $LASTEXITCODE -ne 0) {
    Write-Host "SSH test failed. Add your public key at https://github.com/settings/keys"
    Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
    exit 1
}
git push -u origin master
if ($LASTEXITCODE -eq 0) { Write-Host "Done: https://github.com/0blink0/contract_info" }
