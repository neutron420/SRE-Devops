# ==============================================================
# SRE DevOps Copilot - EC2 Automated Deployment Script
# Deploys the full stack to a single EC2 instance via Docker Compose
# Run from the project root: .\deploy.ps1
# ==============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  SRE DevOps Copilot - EC2 Deployment" -ForegroundColor Cyan
Write-Host "  Cost: ~17 USD/month (vs ~73+ for EKS)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# ----------------- 0. Configuration -----------------
$awsRegion = Read-Host "Enter your AWS Region (default: ap-south-1)"
if ([string]::IsNullOrWhiteSpace($awsRegion)) {
    $awsRegion = "ap-south-1"
}

$instanceType = Read-Host "Enter EC2 instance type (default: t3.small)"
if ([string]::IsNullOrWhiteSpace($instanceType)) {
    $instanceType = "t3.small"
}

# Determine terraform command (check root folder first, then PATH)
$terraformCmd = $null
$localTerraformPath = Join-Path (Get-Location).Path "terraform.exe"
if (Test-Path $localTerraformPath) {
    $terraformCmd = $localTerraformPath
    Write-Host "[INFO] Using local terraform.exe: $terraformCmd" -ForegroundColor Gray
}
elseif (Get-Command "terraform" -ErrorAction SilentlyContinue) {
    $terraformCmd = "terraform"
    Write-Host "[INFO] Using terraform from PATH" -ForegroundColor Gray
}
else {
    Write-Error "Terraform is not installed, not in PATH, and terraform.exe not found in root folder."
}

# ----------------- 1. Prerequisite Checks -----------------
Write-Host ""
Write-Host "[STEP 1/5] Checking prerequisites..." -ForegroundColor Yellow

$requiredTools = @("aws", "ssh", "scp")
foreach ($tool in $requiredTools) {
    if ($null -eq (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "Required tool '$tool' is not installed or not in PATH. Please install it and retry."
    }
}

# Check .env file exists
if (-not (Test-Path ".env")) {
    Write-Error "Missing .env file! Copy .env.example to .env and fill in your API keys first."
}

Write-Host "[OK] All prerequisites verified." -ForegroundColor Green

# ----------------- 2. Provision AWS Infrastructure -----------------
Write-Host ""
Write-Host "[STEP 2/5] Provisioning EC2 infrastructure with Terraform..." -ForegroundColor Yellow
Push-Location terraform

try {
    Write-Host "  Initializing Terraform..." -ForegroundColor Gray
    & $terraformCmd init -upgrade
    if ($LASTEXITCODE -ne 0) { throw "Terraform init failed" }

    Write-Host "  Planning infrastructure changes..." -ForegroundColor Gray
    & $terraformCmd plan -var="aws_region=$awsRegion" -var="instance_type=$instanceType" -out=tfplan
    if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed" }

    Write-Host "  Applying infrastructure..." -ForegroundColor Gray
    & $terraformCmd apply -auto-approve tfplan
    if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }

    # Capture outputs
    $ec2PublicIp = & $terraformCmd output -raw ec2_public_ip
    $sshKeyFile = & $terraformCmd output -raw ssh_key_path
}
finally {
    Pop-Location
}

Write-Host "[OK] EC2 instance created at $ec2PublicIp" -ForegroundColor Green

# Resolve SSH key path to absolute
$sshKeyFullPath = (Resolve-Path "terraform\sre-copilot-key.pem").Path

# Secure the SSH key permissions for Windows OpenSSH client compatibility
if ($env:OS -like "*Windows*") {
    Write-Host "  Securing SSH key file permissions..." -ForegroundColor Gray
    $user = "$env:USERDOMAIN\$env:USERNAME"
    & icacls.exe $sshKeyFullPath /inheritance:r | Out-Null
    & icacls.exe $sshKeyFullPath /grant:r "${user}:R" | Out-Null
}

# ----------------- 3. Wait for EC2 to be ready -----------------
Write-Host ""
Write-Host "[STEP 3/5] Waiting for EC2 instance to be ready..." -ForegroundColor Yellow
Write-Host "  (Docker is being installed via user-data, this takes 2-3 minutes)" -ForegroundColor Gray

$maxRetries = 30
$retryCount = 0
$ready = $false

while (($ready -eq $false) -and ($retryCount -lt $maxRetries)) {
    $retryCount = $retryCount + 1
    Write-Host "  Attempt $retryCount of $maxRetries - checking SSH connectivity..." -ForegroundColor Gray

    $sshResult = $null
    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $sshResult = ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes -i $sshKeyFullPath "ec2-user@$ec2PublicIp" "ls /home/ec2-user/.setup-complete" 2>&1
    }
    catch {
        $sshResult = $null
    }
    $ErrorActionPreference = $prevErrorAction

    if (($null -ne $sshResult) -and ($sshResult -notmatch "No such file") -and ($sshResult -notmatch "Connection refused") -and ($sshResult -notmatch "Permission denied") -and ($LASTEXITCODE -eq 0)) {
        $ready = $true
        Write-Host "[OK] EC2 instance is ready! Docker installed." -ForegroundColor Green
    }
    else {
        Write-Host "  Not ready yet... waiting 15s" -ForegroundColor Gray
        Start-Sleep -Seconds 15
    }
}

if ($ready -eq $false) {
    Write-Error "EC2 instance did not become ready within 7 minutes. Try SSH manually: ssh -i $sshKeyFullPath ec2-user@$ec2PublicIp"
}

# ----------------- 4. Deploy Application Code -----------------
Write-Host ""
Write-Host "[STEP 4/5] Deploying application to EC2..." -ForegroundColor Yellow

$remotePath = "/home/ec2-user/copilot-devops"

# Build list of files to include (skip venv, __pycache__, etc.)
$includeFiles = @(
    "docker-compose.yml",
    ".env",
    "backend-api/Dockerfile",
    "backend-api/.dockerignore",
    "backend-api/requirements.txt",
    "backend-api/app",
    "discord-bot/Dockerfile",
    "discord-bot/.dockerignore",
    "discord-bot/requirements.txt",
    "discord-bot/bot.py",
    "monitoring",
    "docs",
    "kube",
    "landing/Dockerfile",
    "landing/.dockerignore",
    "landing/pnpm-workspace.yaml",
    "landing/eslint.config.mjs",
    "landing/package.json",
    "landing/pnpm-lock.yaml",
    "landing/next.config.mjs",
    "landing/postcss.config.mjs",
    "landing/tsconfig.json",
    "landing/components.json",
    "landing/app",
    "landing/components",
    "landing/hooks",
    "landing/lib",
    "landing/public",
    "landing/styles"
)

# Create a clean staging directory for upload
$stagingDir = Join-Path (Get-Location).Path "deploy-staging"
if (Test-Path $stagingDir) {
    Remove-Item $stagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

Write-Host "  Preparing deployment files..." -ForegroundColor Gray
foreach ($item in $includeFiles) {
    if (Test-Path $item) {
        $destPath = Join-Path $stagingDir $item
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        if (Test-Path $item -PathType Container) {
            Copy-Item $item -Destination $destPath -Recurse -Force
        }
        else {
            Copy-Item $item -Destination $destPath -Force
        }
    }
}
# Clean up any __pycache__ and .pyc files from staging to avoid permission errors on upload
Get-ChildItem -Path $stagingDir -Filter "__pycache__" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $stagingDir -Filter "*.pyc" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "  Uploading project files to EC2..." -ForegroundColor Gray
$stagingItems = Get-ChildItem $stagingDir
foreach ($item in $stagingItems) {
    Write-Host "    Copying $($item.Name)..." -ForegroundColor Gray
    & scp -o StrictHostKeyChecking=no -i $sshKeyFullPath -r $item.FullName "ec2-user@${ec2PublicIp}:${remotePath}/"
}

# Clean up staging
Remove-Item $stagingDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[OK] Files uploaded successfully." -ForegroundColor Green

# ----------------- 5. Start Docker Compose on EC2 -----------------
Write-Host ""
Write-Host "[STEP 5/5] Starting containers with Docker Compose..." -ForegroundColor Yellow

# Create a startup script for the remote server
$startupScriptContent = @(
    '#!/bin/bash',
    'set -e',
    'cd /home/ec2-user/copilot-devops',
    'docker compose down 2>/dev/null || true',
    'echo ">>> Building and starting all containers..."',
    'docker compose up --build -d',
    'echo ">>> Waiting 15s for containers to initialize..."',
    'sleep 15',
    'echo ""',
    'echo ">>> Container Status:"',
    'docker compose ps',
    'echo ""',
    'echo ">>> Checking API health..."',
    'curl -sf http://localhost:8000/health || echo "API still starting up..."'
)
$startupScriptBody = $startupScriptContent -join "`n"

# Write the startup script locally
$localScriptPath = Join-Path (Get-Location).Path "deploy-staging"
New-Item -ItemType Directory -Path $localScriptPath -Force | Out-Null
$localScriptFile = Join-Path $localScriptPath "startup.sh"
[System.IO.File]::WriteAllText($localScriptFile, $startupScriptBody)

# Upload and execute
& scp -o StrictHostKeyChecking=no -i $sshKeyFullPath $localScriptFile "ec2-user@${ec2PublicIp}:/home/ec2-user/startup.sh"
& ssh -o StrictHostKeyChecking=no -i $sshKeyFullPath "ec2-user@$ec2PublicIp" "chmod +x /home/ec2-user/startup.sh; /home/ec2-user/startup.sh"

# Clean up local staging
Remove-Item $localScriptPath -Recurse -Force -ErrorAction SilentlyContinue

# ----------------- Done! -----------------
Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Access your services:" -ForegroundColor White
Write-Host "  API Docs:    http://${ec2PublicIp}:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:      http://${ec2PublicIp}:8000/health" -ForegroundColor Cyan
Write-Host "  Grafana:     http://${ec2PublicIp}:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "  Prometheus:  http://${ec2PublicIp}:9090" -ForegroundColor Cyan
Write-Host ""
Write-Host "  SSH Access:" -ForegroundColor White
Write-Host "  ssh -i $sshKeyFullPath ec2-user@$ec2PublicIp" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Discord Bot: Running automatically using DISCORD_TOKEN from .env" -ForegroundColor White
Write-Host ""
Write-Host "  To update code later: .\deploy.ps1" -ForegroundColor Gray
Write-Host "  To destroy everything: .\cleanup.ps1" -ForegroundColor Gray
Write-Host ""
