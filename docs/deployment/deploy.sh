#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=/opt/logistics-ai-platform/services/06-izg-backend
IMAGE_TAG=${1:-latest}

echo "[1/4] Updating repository..."
cd "$REPO_DIR"
git fetch --all
git checkout main
git pull --ff-only origin main

echo "[2/4] Building Docker image izg-api:$IMAGE_TAG..."
docker build -t registry.binderservices.com/logistics/izg-api:"$IMAGE_TAG" .

echo "[3/4] Pushing image to registry..."
docker push registry.binderservices.com/logistics/izg-api:"$IMAGE_TAG"

echo "[4/4] Restarting systemd service..."
sudo systemctl restart izg-api
sudo systemctl status --no-pager izg-api

echo "Deployment complete."
