#!/bin/bash
set -e
cd /home/ec2-user/copilot-devops
docker compose down 2>/dev/null || true
echo ">>> Building and starting all containers..."
docker compose up --build -d
echo ">>> Waiting 15s for containers to initialize..."
sleep 15
echo ""
echo ">>> Container Status:"
docker compose ps
echo ""
echo ">>> Checking API health..."
curl -sf http://localhost:8000/health || echo "API still starting up..."