# 🚀 Production Deployment Guide: SRE DevOps Copilot

This guide covers deploying the SRE DevOps Copilot to **AWS EC2** using Docker Compose — a cost-effective approach (~$17/month).

---

## 🏛️ Architecture

All services run on a **single EC2 t3.small instance** via Docker Compose:

```text
EC2 Instance (t3.small — 2 vCPU, 2GB RAM)
├── Backend API (FastAPI)     → Port 8000
├── Discord Bot               → Internal only
├── PostgreSQL                → Port 5432
├── Prometheus                → Port 9090
└── Grafana                   → Port 3000
```

### Cost Breakdown

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t3.small | ~$15 |
| EBS 20GB gp3 | ~$1.60 |
| Elastic IP | Free (attached) |
| **Total** | **~$17/month** |

---

## 🛠️ Prerequisites

1. **AWS CLI** configured with credentials (`aws configure`)
2. **Terraform** (or `terraform.exe` in the project root)
3. **SSH** client (built into Windows 10+, macOS, Linux)
4. **`.env` file** with your API keys (copy from `.env.example`)

---

## ⚡ One-Command Deploy

```powershell
.\deploy.ps1
```

This script automates everything:
1. ✅ Checks prerequisites
2. ✅ Provisions EC2 with Terraform (VPC, Security Group, EC2, Elastic IP)
3. ✅ Waits for Docker to install on EC2
4. ✅ Uploads project files via SCP
5. ✅ Starts all containers with Docker Compose

### What you'll be asked:
- **AWS Region** (default: `ap-south-1` Mumbai)
- **Instance Type** (default: `t3.small`)

---

## 🔐 After Deployment

### Access Your Services
- **API Docs**: `http://<EC2_IP>:8000/docs`
- **Health Check**: `http://<EC2_IP>:8000/health`
- **Grafana**: `http://<EC2_IP>:3000` (admin/admin)
- **Prometheus**: `http://<EC2_IP>:9090`

### SSH Into Server
```bash
ssh -i terraform/sre-copilot-key.pem ec2-user@<EC2_IP>
```

### View Container Logs
```bash
ssh -i terraform/sre-copilot-key.pem ec2-user@<EC2_IP> "cd copilot-devops && docker compose logs -f backend-api"
```

---

## 🔄 CI/CD with GitHub Actions

The CI/CD pipeline (`.github/workflows/ci-cd.yml`) automatically deploys on push to `main`.

### Setup Required GitHub Secrets:
1. Go to your GitHub repo → Settings → Secrets and Variables → Actions
2. Add these secrets:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Your EC2 public IP (from Terraform output) |
| `EC2_SSH_KEY` | Contents of `terraform/sre-copilot-key.pem` |

### Pipeline Stages:
1. **Test** → Lint + pytest
2. **Docker Build** → Verify images build
3. **Deploy** → SSH into EC2, rebuild, restart containers (main branch only)

---

## 🧹 Cleanup / Destroy

```powershell
.\cleanup.ps1
```

This destroys all AWS resources (EC2, VPC, EIP) and removes local SSH keys.

---

## 📋 Manual Deployment Steps

If you prefer to deploy manually instead of using `deploy.ps1`:

### Step 1: Provision Infrastructure
```powershell
cd terraform
.\terraform.exe init
.\terraform.exe apply -var="aws_region=ap-south-1"
```

### Step 2: Upload Code to EC2
```bash
scp -i terraform/sre-copilot-key.pem -r docker-compose.yml .env backend-api discord-bot monitoring docs ec2-user@<EC2_IP>:/home/ec2-user/copilot-devops/
```

### Step 3: Start Containers
```bash
ssh -i terraform/sre-copilot-key.pem ec2-user@<EC2_IP> "cd copilot-devops && docker compose up --build -d"
```

---

## 🔧 Troubleshooting

### Containers not starting?
```bash
ssh -i terraform/sre-copilot-key.pem ec2-user@<EC2_IP> "cd copilot-devops && docker compose logs"
```

### Docker not installed yet?
The user data script takes ~2-3 minutes. Check progress:
```bash
ssh -i terraform/sre-copilot-key.pem ec2-user@<EC2_IP> "cat /var/log/user-data.log"
```

### Out of memory?
Upgrade to t3.medium (~$30/month):
```powershell
cd terraform
.\terraform.exe apply -var="instance_type=t3.medium" -auto-approve
```
