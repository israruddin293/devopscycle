# Quick Start Guide

Get the microservices application running in 5 minutes.

## Prerequisites

- Docker Desktop with Kubernetes enabled, OR
- Minikube installed

## Option 1: Docker Desktop (Easiest)

### 1. Enable Kubernetes
- Open Docker Desktop
- Go to Settings → Kubernetes
- Check "Enable Kubernetes"
- Click "Apply & Restart"

### 2. Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd project

# Build images
docker build -t backend:latest ./backend
docker build -t frontend:latest ./frontend

# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Enable ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

### 3. Configure DNS

Add to /etc/hosts (Mac/Linux) or C:\Windows\System32\drivers\etc\hosts (Windows):
```
127.0.0.1 microservices.local
```

### 4. Access Application

Open browser: http://microservices.local

## Option 2: Minikube

### 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Build Images

```bash
# Use minikube's Docker daemon
eval $(minikube docker-env)

# Build images
docker build -t backend:latest ./backend
docker build -t frontend:latest ./frontend
```

### 3. Deploy Application

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### 4. Configure DNS

```bash
# Get minikube IP
minikube ip

# Add to /etc/hosts
echo "$(minikube ip) microservices.local" | sudo tee -a /etc/hosts
```

### 5. Access Application

Open browser: http://microservices.local

## Option 3: Using Helm

```bash
# Install with Helm
helm install microservices ./helm

# Wait for pods
kubectl wait --for=condition=ready pod -l app=backend -n microservices --timeout=300s

# Configure DNS (same as above)

# Access application
open http://microservices.local
```

## Verify Deployment

```bash
# Check pods
kubectl get pods -n microservices

# Expected output:
# NAME                        READY   STATUS    RESTARTS   AGE
# backend-xxx                 1/1     Running   0          2m
# frontend-xxx                1/1     Running   0          2m
# redis-xxx                   1/1     Running   0          2m

# Check services
kubectl get svc -n microservices

# Check ingress
kubectl get ingress -n microservices
```

## Test Endpoints

```bash
# Frontend health
curl http://microservices.local/health

# Backend health
curl http://microservices.local/api/health

# Backend API
curl http://microservices.local/api/data
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n microservices
kubectl logs <pod-name> -n microservices
```

### Ingress not working
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress
kubectl describe ingress microservices-ingress -n microservices
```

### Cannot access application
```bash
# Verify DNS
ping microservices.local

# Check if ingress controller is running
kubectl get svc -n ingress-nginx
```

## Clean Up

```bash
# Delete all resources
kubectl delete namespace microservices

# Stop minikube (if using)
minikube stop
```

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Review [SECURITY.md](SECURITY.md) for security best practices
- Check [CI-CD.md](CI-CD.md) for pipeline setup
- Explore [ARCHITECTURE.md](ARCHITECTURE.md) for system design
