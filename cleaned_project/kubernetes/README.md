# Kubernetes Deployment for AI Blogging Butler

This directory contains the Kubernetes manifests needed to deploy the AI Blogging Butler to a Kubernetes cluster.

## Components

- **CronJob**: Schedules the AI Blogging Butler to run on a regular basis (hourly by default)
- **Secrets**: Stores WordPress credentials and AWS credentials securely
- **Container Build**: Scripts for building multi-architecture Docker images

## Deployment

To deploy the AI Blogging Butler to your Kubernetes cluster:

1. Build and push the Docker image:
   ```bash
   cd ../
   ./kubernetes/container-build/build_multiarch_fixed.sh
   ```
   This script will:
   - Build multi-architecture Docker images (ARM64 and AMD64)
   - Push the images to Docker Hub
   - Update the Kubernetes manifests with the correct image
   - Create and apply the necessary secrets

2. Alternatively, create the required secrets manually:
   ```bash
   # Create from template
   cp kubernetes/secrets-template.yaml kubernetes/secrets/secrets-actual.yaml
   
   # Edit the file to add your credentials
   nano kubernetes/secrets/secrets-actual.yaml
   
   # Apply the secrets
   kubectl apply -f kubernetes/secrets/secrets-actual.yaml
   ```

3. Deploy the CronJob:
   ```bash
   kubectl apply -f kubernetes/cronjob-actual.yaml
   ```

## Managing the CronJob

- **Check status**: `kubectl get cronjobs`
- **Suspend posting**: `kubectl patch cronjob ai-blogging-butler-scheduler -p '{"spec":{"suspend":true}}'`
- **Resume posting**: `kubectl patch cronjob ai-blogging-butler-scheduler -p '{"spec":{"suspend":false}}'`
- **Trigger manually**: `kubectl create job --from=cronjob/ai-blogging-butler-scheduler manual-post`
- **View logs**: `kubectl logs job/ai-blogging-butler-scheduler-<job-id>`

## Security Notes

- Never commit actual secrets to Git
- Use environment variables or a secure secrets manager in production
- The `secrets-actual.yaml` file is in `.gitignore` to prevent accidental commits

## Cleanup

To remove the deployment:
```bash
kubectl delete -f kubernetes/cronjob-actual.yaml
kubectl delete -f kubernetes/secrets/secrets-actual.yaml
```
