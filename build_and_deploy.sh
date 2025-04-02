#!/bin/bash

# Build and deploy The AI Blogging Butler to Kubernetes
# This script builds the Docker image, pushes it to Docker Hub, and deploys to Kubernetes

echo "🎩 Building and deploying The AI Blogging Butler to Kubernetes 🎩"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

# Skip Docker Hub login check - we're already logged in
echo "🔑 Using existing Docker Hub credentials..."

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t fdebene/ai-butler:latest .

# Push to Docker Hub
echo "🚀 Pushing to Docker Hub..."
docker push fdebene/ai-butler:latest

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
