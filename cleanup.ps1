

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Red
Write-Host "  SRE DevOps Copilot - CLEANUP / DESTROY" -ForegroundColor Red
Write-Host "==============================================" -ForegroundColor Red
Write-Host ""

# Confirmation prompt
$confirm = Read-Host "This will DESTROY all AWS resources (EC2, VPC, EIP). Are you sure? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

# Determine terraform command
$localTerraform = Test-Path ".\terraform.exe"
$terraformCmd = "terraform"
if ($localTerraform) {
    $terraformCmd = Join-Path (Get-Item .).FullName "terraform.exe"
    Write-Host "[INFO] Using local terraform.exe: $terraformCmd" -ForegroundColor Gray
}

# Check prerequisite
if (-not $localTerraform -and ($null -eq (Get-Command "terraform" -ErrorAction SilentlyContinue))) {
    Write-Error "Terraform is not installed, not in PATH, and terraform.exe not found in root folder."
}

# Destroy infrastructure
Write-Host "`n[STEP 1/2] Destroying AWS infrastructure..." -ForegroundColor Yellow
Push-Location terraform

try {
    & $terraformCmd init -upgrade 2>$null
    & $terraformCmd destroy -auto-approve
}
finally {
    Pop-Location
}

# Clean up local key file
Write-Host "`n[STEP 2/2] Cleaning up local files..." -ForegroundColor Yellow
$keyFile = "terraform\sre-copilot-key.pem"
if (Test-Path $keyFile) {
    # Reset file permissions (Terraform sets it to read-only 0400 which blocks deletion on Windows)
    if ($IsWindows -or $env:OS -like "*Windows*") {
        icacls.exe $keyFile /reset | Out-Null
    }
    Remove-Item $keyFile -Force
    Write-Host "  Removed SSH key: $keyFile" -ForegroundColor Gray
}


# Clean up terraform plan file
$planFile = "terraform\tfplan"
if (Test-Path $planFile) {
    Remove-Item $planFile -Force
    Write-Host "  Removed plan file: $planFile" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "  All AWS resources have been destroyed." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
