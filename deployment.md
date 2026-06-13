# 🚀 Production Deployment Guide: SRE DevOps Copilot

This guide outlines **the best way to deploy** the SRE DevOps Copilot in a production enterprise environment.

---

## 🏛️ Recommended Production Topology

The absolute best way to deploy this application is **directly inside your production Kubernetes cluster** alongside the services you want to monitor.

### Why this is the best way:
1. **Security & RBAC**: The FastAPI backend pod can use a native Kubernetes ServiceAccount (`sre-copilot-sa`) to query logs and events securely inside the cluster without exposing credentials outside the network.
2. **Network Performance**: The Prometheus service is queried internally via fast cluster DNS (e.g., `http://prometheus-service.monitoring.svc.cluster.local:9090`), bypassing public load balancers.
3. **High Availability & Volume Mounts**: Kubernetes automatically manages container lifecycle restarts, scaling, and mounts persistent volumes (via PersistentVolumeClaims) for ChromaDB RAG documents.

---

## 🛠️ Step-by-Step Deployment Walkthrough

### Step 1: Build & Push Docker Images
First, build the Docker images for the backend API and the Discord bot, then push them to a container registry of your choice (Docker Hub, AWS ECR, GCP Artifact Registry, GitHub Container Registry, etc.).

```bash
# Define your registry prefix
REGISTRY="your-docker-registry-username"

# 1. Build and push the Backend API
docker build -t $REGISTRY/devops-copilot-backend:latest ./backend-api
docker push $REGISTRY/devops-copilot-backend:latest

# 2. Build and push the Discord Bot
docker build -t $REGISTRY/devops-copilot-bot:latest ./discord-bot
docker push $REGISTRY/devops-copilot-bot:latest
```

---

### Step 2: Configure secrets in Kubernetes
Create a Kubernetes Secret named `copilot-secrets` containing your live environment details. Replace the placeholder values with your real tokens:

```bash
kubectl create secret generic copilot-secrets \
  --from-literal=GEMINI_API_KEY="your_actual_gemini_api_key" \
  --from-literal=DISCORD_TOKEN="your_actual_discord_bot_token" \
  --from-literal=DATABASE_URL="postgresql://neondb_owner:password@ep-host-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require" \
  --namespace=default
```

---

### Step 3: Apply RBAC authorization Roles
The backend requires list/get/watch permissions for pods, logs, events, and deployments. Apply the RBAC resource file:

```bash
kubectl apply -f kubernetes/sre-rbac.yaml
```

---

### Step 4: Configure & deploy the services
1. Open `kubernetes/sre-deployments.yaml` and update the image tags to point to your registry:
   * Line 46: Change `image: devops-copilot-backend:latest` to `image: your-docker-registry-username/devops-copilot-backend:latest`.
   * Line 88: Change `image: devops-copilot-bot:latest` to `image: your-docker-registry-username/devops-copilot-bot:latest`.
2. Check the Prometheus server connection address:
   * Line 57: Update the `PROMETHEUS_URL` value to your cluster's Prometheus Service endpoint (e.g. `http://prometheus-service.monitoring.svc.cluster.local:9090`).
3. Apply the manifests:
   ```bash
   kubectl apply -f kubernetes/sre-deployments.yaml
   ```

---

## 🔄 Lifecycle & Maintenance Tasks

### Adding Runbooks dynamically
To add runbooks to your ChromaDB RAG assistant:
1. Save your markdown troubleshooting guides (`.md` or `.txt`) inside the `docs/runbooks` directory.
2. The FastAPI backend automatically loads and indexes any new documents found in this directory on startup.
3. You can also upload files dynamically using the `/upload-doc` API route or Discord attachment commands in future integrations.

### Scaling & High Availability notes
* **Discord Bot**: Keep `replicas: 1` for the `sre-discord-bot` deployment to prevent duplicate webhook callbacks and redundant slash command registrations.
* **FastAPI Backend**: Can be scaled up to multiple replicas behind a Service load balancer. Since database logging is saved to Neon DB, the api endpoints are stateless.
