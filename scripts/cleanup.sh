#!/bin/bash

# Cleanup script for Whisper Transcription Service
# Usage: ./scripts/cleanup.sh [KEEP_NAMESPACE]

set -e

KEEP_NAMESPACE="${1:-false}"

echo "Cleaning up Whisper Transcription Service from Kubernetes..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Navigate to k8s directory
cd k8s

echo "Removing resources..."
kubectl delete -k . --ignore-not-found=true

if [ "$KEEP_NAMESPACE" = "false" ]; then
    echo "Removing namespace..."
    kubectl delete namespace transcription-service --ignore-not-found=true
else
    echo "Keeping namespace as requested..."
fi

echo "Cleanup completed successfully!" 