# DevOps Copilot AWS EKS Automatic Deployment Script
# Run this from the root directory of the project in PowerShell.

$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Starting SRE DevOps Copilot Deployment" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# ----------------- 0. Configuration & Prompts -----------------
$awsAccountId = Read-Host "Enter your AWS Account ID (12 digits)"
if ($awsAccountId -match "^\d{12}$" -eq $false) {
    Write-Error "Invalid AWS Account ID. Must be 12 digits."
}

$awsRegion = Read-Host "Enter your AWS Region (e.g. us-east-1)"
if ([string]::IsNullOrWhiteSpace($awsRegion)) {
    Write-Error "AWS Region cannot be empty."
}

# ----------------- 1. Prerequisite Checks -----------------
Write-Host "`n[INFO] Checking prerequisites..." -ForegroundColor Yellow

$tools = @("aws", "docker", "terraform", "kubectl")
foreach ($tool in $tools) {
    if ((Get-Command $tool -ErrorAction SilentlyContinue) -eq $null) {
        Write-Error "Prerequisite tool '$tool' is not installed or not in your PATH. Please install it and retry."
    }
}
Write-Host "[SUCCESS] All prerequisite tools (aws, docker, terraform, kubectl) are installed." -ForegroundColor Green

# ----------------- 2. AWS Infrastructure (Stage 1) -----------------
Write-Host "`n[STAGE 1] Creating EKS Cluster and ECR Registries..." -ForegroundColor Yellow
Push-Location terraform

try {
    Write-Host "Initializing Terraform..." -ForegroundColor Gray
    terraform init
    Write-Host "Applying Terraform configuration..." -ForegroundColor Gray
    # Automatically apply with the chosen region variable
    terraform apply -var="aws_region=$awsRegion" -auto-approve
}
finally {
    Pop-Location
}
Write-Host "[SUCCESS] Stage 1 Complete: AWS Infrastructure built successfully." -ForegroundColor Green

# ----------------- 3. Docker Build & Push (Stage 2) -----------------
$registryUri = "${awsAccountId}.dkr.ecr.${awsRegion}.amazonaws.com"
Write-Host "`n[STAGE 2] Building and pushing Docker images to $registryUri..." -ForegroundColor Yellow

# ECR Login
Write-Host "Logging in to AWS ECR..." -ForegroundColor Gray
aws ecr get-login-password --region $awsRegion | docker login --username AWS --password-stdin $registryUri

# Build and Push Backend API
Write-Host "Building Backend API image..." -ForegroundColor Gray
docker build -t devops-copilot-backend ./backend-api
docker tag devops-copilot-backend:latest "${registryUri}/devops-copilot-backend:latest"
Write-Host "Pushing Backend API image to ECR..." -ForegroundColor Gray
docker push "${registryUri}/devops-copilot-backend:latest"

# Build and Push Discord Bot
Write-Host "Building Discord Bot image..." -ForegroundColor Gray
docker build -t devops-copilot-bot ./discord-bot
docker tag devops-copilot-bot:latest "${registryUri}/devops-copilot-bot:latest"
Write-Host "Pushing Discord Bot image to ECR..." -ForegroundColor Gray
docker push "${registryUri}/devops-copilot-bot:latest"

Write-Host "[SUCCESS] Stage 2 Complete: Docker images pushed to ECR." -ForegroundColor Green

# ----------------- 4. Kubernetes Deployment (Stage 3) -----------------
Write-Host "`n[STAGE 3] Deploying applications to EKS Cluster..." -ForegroundColor Yellow

# Connect kubeconfig
Write-Host "Connecting kubectl to EKS..." -ForegroundColor Gray
aws eks update-kubeconfig --region $awsRegion --name sre-copilot-cluster

# Load variables from .env file
Write-Host "Reading secrets from .env..." -ForegroundColor Gray
if (Test-Path ".env") {
    $envContent = Get-Content ".env"
    $geminiKey = ""
    $discordToken = ""
    $databaseUrl = ""

    foreach ($line in $envContent) {
        if ($line -match "^GEMINI_API_KEY=(.+)$") { $geminiKey = $Matches[1].Trim() }
        if ($line -match "^DISCORD_TOKEN=(.+)$") { $discordToken = $Matches[1].Trim() }
        if ($line -match "^DATABASE_URL=(.+)$") { $databaseUrl = $Matches[1].Trim() }
    }
} else {
    Write-Error "Local .env file not found in root directory!"
}

# Create Kubernetes Secret (Idempotent using dry-run)
Write-Host "Creating Kubernetes secrets..." -ForegroundColor Gray
kubectl create secret generic copilot-secrets `
  --from-literal=GEMINI_API_KEY="$geminiKey" `
  --from-literal=DISCORD_TOKEN="$discordToken" `
  --from-literal=DATABASE_URL="$databaseUrl" `
  --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC Config
Write-Host "Applying cluster RBAC configuration..." -ForegroundColor Gray
kubectl apply -f kubernetes/sre-rbac.yaml

# Modify deployment manifest in-memory to inject ECR URIs and deploy
Write-Host "Deploying SRE backend and Discord bot..." -ForegroundColor Gray
$deploymentManifest = Get-Content "kubernetes/sre-deployments.yaml" -Raw
$deploymentManifest = $deploymentManifest -replace "image: devops-copilot-backend:latest", "image: ${registryUri}/devops-copilot-backend:latest"
$deploymentManifest = $deploymentManifest -replace "image: devops-copilot-bot:latest", "image: ${registryUri}/devops-copilot-bot:latest"

# Pipe modified manifest directly into kubectl
$deploymentManifest | kubectl apply -f -

Write-Host "[SUCCESS] Stage 3 Complete: Applications deployed successfully." -ForegroundColor Green

Write-Host "`n=============================================" -ForegroundColor Green
Write-Host "Deployment completed successfully." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
