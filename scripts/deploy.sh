#!/bin/bash

# Deployment script for Whisper Transcription Service on Kubernetes
# Usage: ./scripts/deploy.sh [ENVIRONMENT] [DRY_RUN]

set -e

ENVIRONMENT="${1:-production}"
DRY_RUN="${2:-false}"

echo "Deploying Whisper Transcription Service to Kubernetes..."
echo "Environment: $ENVIRONMENT"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "Error: kustomize is not installed or not in PATH"
    echo "You can install it with: kubectl kustomize --help"
    exit 1
fi

# Verify cluster connection
echo "Verifying cluster connection..."
kubectl cluster-info

# Navigate to k8s directory
cd k8s

# Apply the manifests
if [ "$DRY_RUN" = "true" ]; then
    echo "Running in dry-run mode..."
    kubectl apply --dry-run=client -k .
else
    echo "Applying Kubernetes manifests..."
    kubectl apply -k .
    
    echo "Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/whisper-transcription -n transcription-service
    
    echo "Checking pod status..."
    kubectl get pods -n transcription-service -l app=whisper-transcription
    
    echo "Checking service status..."
    kubectl get svc -n transcription-service
    
    echo "Deployment completed successfully!"
    echo ""
    echo "To check the status of your deployment:"
    echo "  kubectl get all -n transcription-service"
    echo ""
    echo "To view logs:"
    echo "  kubectl logs -n transcription-service -l app=whisper-transcription -f"
    echo ""
    echo "To access the service locally:"
    echo "  kubectl port-forward -n transcription-service svc/whisper-transcription-service 8000:80"
fi 