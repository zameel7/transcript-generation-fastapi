#!/bin/bash

# Build and push script for Whisper Transcription Service
# Usage: ./scripts/build-and-push.sh [IMAGE_TAG] [REGISTRY]

set -e

# Configuration
IMAGE_NAME="whisper-transcription"
IMAGE_TAG="${1:-latest}"
REGISTRY="${2:-}"
DOCKERFILE="Dockerfile"

# If registry is provided, prefix the image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$IMAGE_TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$IMAGE_TAG"
fi

echo "Building Docker image: $FULL_IMAGE_NAME"

# Build the image
docker build -t "$FULL_IMAGE_NAME" -f "$DOCKERFILE" .

echo "Docker image built successfully: $FULL_IMAGE_NAME"

# Push to registry if specified
if [ -n "$REGISTRY" ]; then
    echo "Pushing image to registry..."
    docker push "$FULL_IMAGE_NAME"
    echo "Image pushed successfully!"
    
    # Update kustomization.yaml with new image
    echo "Updating kustomization.yaml with new image tag..."
    cd k8s
    sed -i.bak "s/newTag: .*/newTag: $IMAGE_TAG/" kustomization.yaml
    rm kustomization.yaml.bak
    echo "kustomization.yaml updated with tag: $IMAGE_TAG"
else
    echo "No registry specified. Image built locally only."
    echo "To deploy to Kubernetes, make sure the image is available in your cluster."
fi

echo "Build completed successfully!"
echo "Image: $FULL_IMAGE_NAME" 