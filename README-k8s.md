# Kubernetes Deployment Guide

This guide explains how to deploy the Whisper FastAPI Transcription Service to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.19+)
- kubectl configured to access your cluster
- Docker registry access (for pushing images)
- NGINX Ingress Controller (optional, for external access)
- cert-manager (optional, for automatic SSL certificates)

## Quick Start

1. **Build and push the Docker image:**
   ```bash
   chmod +x scripts/build-and-push.sh
   ./scripts/build-and-push.sh latest your-registry.com
   ```

2. **Deploy to Kubernetes:**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

3. **Access the service:**
   ```bash
   kubectl port-forward -n transcription-service svc/whisper-transcription-service 8000:80
   ```

## Architecture Overview

The deployment consists of:

- **Namespace**: `transcription-service` - Isolates resources
- **Deployment**: Runs 2 replicas of the FastAPI application
- **Service**: Exposes the application within the cluster
- **Ingress**: Provides external access (optional)
- **ConfigMap**: Manages environment variables
- **PVC**: Persists Whisper model cache
- **HPA**: Auto-scales based on CPU/memory usage
- **PDB**: Ensures high availability during updates
- **NetworkPolicy**: Controls network traffic for security

## Configuration

### Environment Variables

Configure the application through the ConfigMap in `k8s/configmap.yaml`:

```yaml
data:
  WHISPER_MODEL: "turbo"  # Options: tiny, base, small, medium, large, turbo
  WHISPER_CACHE_DIR: "/app/cache"
  PYTHONUNBUFFERED: "1"
  PYTHONDONTWRITEBYTECODE: "1"
```

### Resource Requirements

The deployment is configured with:
- **Requests**: 2GB RAM, 1 CPU
- **Limits**: 8GB RAM, 4 CPU

Adjust these based on your chosen Whisper model:
- `tiny`/`base`: 2GB RAM minimum
- `small`: 4GB RAM minimum
- `medium`: 8GB RAM minimum
- `large`/`turbo`: 8GB+ RAM minimum

### Storage

A 10GB PersistentVolume is used to cache Whisper models. Adjust the size in `k8s/pvc.yaml` if needed.

## Deployment Options

### 1. Using Kustomize (Recommended)

```bash
# Deploy
kubectl apply -k k8s/

# Check status
kubectl get all -n transcription-service
```

### 2. Using Individual Manifests

```bash
# Apply in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/poddisruptionbudget.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/ingress.yaml  # Optional
```

### 3. Using Scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Build and push image
./scripts/build-and-push.sh v1.0.0 your-registry.com

# Deploy
./scripts/deploy.sh

# Cleanup when done
./scripts/cleanup.sh
```

## External Access

### Option 1: Port Forward (Development)

```bash
kubectl port-forward -n transcription-service svc/whisper-transcription-service 8000:80
```

Access at: http://localhost:8000

### Option 2: Ingress (Production)

1. **Install NGINX Ingress Controller:**
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   ```

2. **Update the Ingress configuration:**
   Edit `k8s/ingress.yaml` and replace `transcription.yourdomain.com` with your actual domain.

3. **Apply the Ingress:**
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

### Option 3: LoadBalancer (Cloud)

Change the service type to LoadBalancer:

```yaml
# In k8s/service.yaml
spec:
  type: LoadBalancer
```

## SSL/TLS Configuration

For automatic SSL certificates with Let's Encrypt:

1. **Install cert-manager:**
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml
   ```

2. **Create ClusterIssuer:**
   ```bash
   kubectl apply -f - <<EOF
   apiVersion: cert-manager.io/v1
   kind: ClusterIssuer
   metadata:
     name: letsencrypt-prod
   spec:
     acme:
       server: https://acme-v02.api.letsencrypt.org/directory
       email: your-email@example.com
       privateKeySecretRef:
         name: letsencrypt-prod
       solvers:
       - http01:
           ingress:
             class: nginx
   EOF
   ```

## Monitoring and Observability

### Health Checks

The application provides health endpoints:
- `/` - Basic status
- `/health` - Detailed health with model info

### Logging

View application logs:
```bash
# All pods
kubectl logs -n transcription-service -l app=whisper-transcription -f

# Specific pod
kubectl logs -n transcription-service <pod-name> -f
```

### Metrics

The HPA monitors CPU and memory usage. For more detailed metrics, consider installing:
- Prometheus
- Grafana
- Kubernetes metrics server

## Scaling

### Manual Scaling

```bash
kubectl scale deployment whisper-transcription -n transcription-service --replicas=5
```

### Auto Scaling

The HPA automatically scales between 2-10 replicas based on:
- CPU usage > 70%
- Memory usage > 80%

## Security

### Network Policies

The deployment includes NetworkPolicy for:
- Allowing ingress from NGINX controller
- Allowing egress for model downloads
- Restricting other traffic

### Service Account

A dedicated ServiceAccount is created with minimal permissions.

### Pod Security

- Runs as non-root user
- No privilege escalation
- Read-only root filesystem (where possible)

## Troubleshooting

### Common Issues

1. **Model download fails:**
   - Check internet connectivity
   - Verify proxy settings if behind corporate firewall
   - Check storage space

2. **Out of memory errors:**
   - Increase memory limits in deployment
   - Use smaller Whisper model
   - Reduce number of replicas

3. **Slow startup:**
   - Models are downloaded on first run
   - Consider pre-building image with models
   - Increase startup probe timeout

### Debugging Commands

```bash
# Check pod status
kubectl get pods -n transcription-service

# Describe pod for events
kubectl describe pod -n transcription-service <pod-name>

# Check logs
kubectl logs -n transcription-service <pod-name>

# Shell into pod
kubectl exec -it -n transcription-service <pod-name> -- /bin/bash

# Check resource usage
kubectl top pods -n transcription-service
```

## Updating the Deployment

1. **Build new image:**
   ```bash
   ./scripts/build-and-push.sh v1.1.0 your-registry.com
   ```

2. **Update deployment:**
   ```bash
   kubectl set image deployment/whisper-transcription -n transcription-service whisper-transcription=your-registry.com/whisper-transcription:v1.1.0
   ```

3. **Check rollout status:**
   ```bash
   kubectl rollout status deployment/whisper-transcription -n transcription-service
   ```

## Cleanup

Remove all resources:
```bash
./scripts/cleanup.sh
```

Or manually:
```bash
kubectl delete -k k8s/
```

## Production Considerations

1. **Resource Limits**: Set appropriate limits based on your workload
2. **Persistent Storage**: Consider using faster storage classes for better performance
3. **Backup**: Implement backup strategy for model cache
4. **Monitoring**: Set up comprehensive monitoring and alerting
5. **Security**: Regular security scans and updates
6. **Load Testing**: Test with expected load patterns
7. **Disaster Recovery**: Plan for multi-region deployments if needed

## Support

For issues and questions:
1. Check the application logs
2. Review Kubernetes events
3. Consult the FastAPI documentation
4. Check OpenAI Whisper documentation 