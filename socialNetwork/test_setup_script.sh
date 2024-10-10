#!/bin/bash

# Namespace to check
NAMESPACE="monitoring"
# Interval in seconds between checks
INTERVAL=10
# Timeout in seconds
TIMEOUT=300
# Time spent waiting
elapsed=0

echo "Waiting for pods in '$NAMESPACE' namespace to be running..."

while [ $elapsed -lt $TIMEOUT ]; do
    # Get the status of pods
    NOT_RUNNING=$(kubectl get pods -n $NAMESPACE --no-headers | grep -v 'Running' | wc -l)
    if [ $NOT_RUNNING -eq 0 ]; then
        echo "All pods are in the running state."
        exit 0
    else
        echo "Waiting for $NOT_RUNNING pods to enter Running state..."
        sleep $INTERVAL
        elapsed=$((elapsed + INTERVAL))
    fi
done

echo "Timeout reached. Not all pods are running."
exit 1

