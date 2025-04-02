# Kubernetes Deployment for The AI Blogging Butler

Because manually deploying your AI butler is *so* last week. This guide will help you deploy The AI Blogging Butler to your Kubernetes cluster and schedule it to run hourly.

## Prerequisites

- A Kubernetes cluster (because what's the point of having Kubernetes if you're not going to use it?)
- Docker installed locally (for building the image)
- kubectl configured to talk to your cluster (otherwise you're just shouting commands into the void)
- A container registry (Docker Hub, ECR, GCR, or whatever floats your container boat)

## Setup Instructions

### 1. Build and Push the Docker Image

```bash
# Navigate to the project directory
cd /path/to/wp

# Build the Docker image
docker build -t your-registry/ai-blogging-butler:latest .

# Push to your registry
docker push your-registry/ai-blogging-butler:latest
```

### 2. Update Kubernetes Manifests

Edit the following files to replace placeholders:

1. In `kubernetes/deployment.yaml` and `kubernetes/cronjob.yaml`:
   - Replace `${YOUR_REGISTRY}` with your actual container registry path

2. In `kubernetes/secrets.yaml`:
   - Update the WordPress credentials
   - Update the AWS credentials

### 3. Apply the Kubernetes Manifests

```bash
# Create the secrets first
kubectl apply -f kubernetes/secrets.yaml

# Deploy the application
kubectl apply -f kubernetes/deployment.yaml

# Or if you prefer to use the CronJob instead of a persistent deployment
kubectl apply -f kubernetes/cronjob.yaml
```

## How It Works

1. The container starts and checks for mounted credentials
2. It copies the credentials to the working directory
3. It runs the AI Blogging Butler script
4. If deployed as a CronJob, it runs hourly to check for GitHub updates and generate new posts

## Troubleshooting

- Pods crashing? Check the logs with `kubectl logs <pod-name>`
- Credentials not working? Make sure your secrets are correctly formatted
- Images not generating? Ensure your AWS credentials have access to Bedrock
- Everything broken? At least you have Kubernetes to blame now!

Remember: If all else fails, you can always fall back to running the script manually like a caveman.
