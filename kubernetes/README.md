# Kubernetes Deployment for AI Blogging Butler

This directory contains the Kubernetes manifests needed to deploy the AI Blogging Butler to a Kubernetes cluster.

## Components

- **CronJob**: Schedules the AI Blogging Butler to run on a regular basis (hourly by default)
- **Secrets**: Stores WordPress credentials and AWS credentials securely

## Deployment

To deploy the AI Blogging Butler to your Kubernetes cluster:

1. Create the necessary secrets:
   ```bash
   # Create a secrets-actual.yaml file with your credentials
   # DO NOT commit this file to Git!
   ```

2. Apply the secrets to your cluster:
   ```bash
   kubectl apply -f kubernetes/secrets-actual.yaml
   ```

3. Apply the CronJob to your cluster:
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
