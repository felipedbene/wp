#!/bin/bash

# Build and deploy The AI Blogging Butler to Kubernetes with multi-architecture support
# This script builds Docker images for both ARM64 and AMD64, creates a manifest, and deploys to Kubernetes

echo "🎩 Building multi-architecture images for The AI Blogging Butler 🎩"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

# Create builder if it doesn't exist
if ! docker buildx ls | grep -q "multiarch"; then
  echo "🔧 Creating multi-architecture builder..."
  docker buildx create --name multiarch --driver docker-container --use
fi

# Use the builder
docker buildx use multiarch

# Build and push multi-architecture images
echo "🔨 Building and pushing multi-architecture images..."
docker buildx build --platform linux/amd64,linux/arm64 \
  -t fdebene/ai-butler:latest \
  --push .

echo "✅ Multi-architecture images built and pushed successfully!"

# Update the CronJob to use the correct image
echo "🔄 Updating Kubernetes manifests with correct image..."
sed -i '' 's|felipedbene/ai-blogging-butler:latest|fdebene/ai-butler:latest|g' kubernetes/cronjob-actual.yaml

# Create secrets from environment variables
echo "🔑 Creating Kubernetes secrets..."
export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)

# Get WordPress password from blog-credentials.json
WP_PASSWORD=$(grep -o '"password": "[^"]*"' blog-credentials.json | cut -d'"' -f4)

# Replace placeholders in secrets-actual.yaml
sed -i '' "s/REDACTED_PASSWORD/$WP_PASSWORD/g" kubernetes/secrets-actual.yaml
envsubst < kubernetes/secrets-actual.yaml > kubernetes/secrets-ready.yaml

# Apply secrets to Kubernetes
kubectl apply -f kubernetes/secrets-ready.yaml

# Apply CronJob to Kubernetes
echo "⏰ Deploying CronJob to Kubernetes..."
kubectl apply -f kubernetes/cronjob-actual.yaml

# Clean up sensitive files
rm kubernetes/secrets-ready.yaml

echo "✅ Deployment complete! The AI Blogging Butler is now running in your Kubernetes cluster."
echo "📊 Check status with: kubectl get cronjobs"
echo "📝 View logs with: kubectl logs job/ai-blogging-butler-scheduler-<job-id>"
