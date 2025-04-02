# Additional Kubernetes Manifests

This directory contains additional Kubernetes manifests that might be useful for deploying and managing the AI Blogging Butler.

## Available Manifests

You can create the following manifests as needed:

1. **Debug Pod**: For troubleshooting issues in the Kubernetes environment
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: debug-pod
   spec:
     containers:
     - name: debug
       image: fdebene/ai-butler:latest
       command: ["sleep", "3600"]
       volumeMounts:
       - name: credentials
         mountPath: "/app/credentials"
         readOnly: true
     volumes:
     - name: credentials
       secret:
         secretName: blog-credentials
   ```

2. **Test Connection Job**: For testing connectivity to WordPress and AWS
   ```yaml
   apiVersion: batch/v1
   kind: Job
   metadata:
     name: test-connection
   spec:
     template:
       spec:
         containers:
         - name: test-connection
           image: fdebene/ai-butler:latest
           command: ["python", "-c", "import boto3; import wordpress_xmlrpc; print('Connection test successful')"]
           volumeMounts:
           - name: credentials
             mountPath: "/app/credentials"
             readOnly: true
           - name: aws-credentials
             mountPath: "/root/.aws"
             readOnly: true
         volumes:
         - name: credentials
           secret:
             secretName: blog-credentials
         - name: aws-credentials
           secret:
             secretName: aws-credentials
         restartPolicy: Never
     backoffLimit: 1
   ```

## Usage

To apply any of these manifests:

1. Create the manifest file in this directory
2. Apply it with kubectl:
   ```bash
   kubectl apply -f kubernetes/manifests/your-manifest.yaml
   ```
