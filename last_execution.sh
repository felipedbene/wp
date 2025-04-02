#!/bin/bash

# Usage: ./last_execution.sh [job-name-prefix]
JOB_PREFIX=${1:-ai-blogging-butler-scheduler}

echo "🔍 Finding latest Job with prefix: $JOB_PREFIX..."

# Get the latest job name by creation timestamp
LATEST_JOB=$(kubectl get jobs \
  --sort-by=.metadata.creationTimestamp \
  --no-headers \
  | grep "^$JOB_PREFIX" \
  | tail -n 1 \
  | awk '{print $1}')

if [ -z "$LATEST_JOB" ]; then
  echo "❌ No job found with prefix '$JOB_PREFIX'"
  exit 1
fi

echo "✅ Latest Job: $LATEST_JOB"

# Get the pod name associated with that job
POD_NAME=$(kubectl get pods \
  --selector=job-name=$LATEST_JOB \
  --output=jsonpath="{.items[0].metadata.name}")

if [ -z "$POD_NAME" ]; then
  echo "❌ No pod found for job '$LATEST_JOB'"
  exit 1
fi

echo "📦 Fetching logs from Pod: $POD_NAME"
echo "---------------------------------------"
kubectl logs "$POD_NAME"