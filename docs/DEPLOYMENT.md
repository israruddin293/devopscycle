# Deployment Guide

## Prerequisites

### Required Tools
- kubectl 1.25+
- Docker 20.10+
- Kubernetes cluster (1.25+)
- Git

### Cluster Options
1. Local: minikube, kind, Docker Desktop
2. Cloud: EKS, GKE, AKS
3. On-premise: kubeadm, k3s

## Step-by-Step Deployment

### 1. Prepare Kubernetes Cluster

#### Option A: Minikube
```bash
# Start minikube
minikube start --cpus=4 --memory=8192

# Enable ingress
minikube addons enable ingress

# Enable metrics server
minikube addons enable metrics-server
```

#### Option B: Kind
```bash
# Create cluster with ingress support
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

#### Option C: Cloud Provider
```bash
# AWS EKS
eksctl create cluster --name microservices --region us-west-2

# GCP GKE
gcloud container clusters create microservices --zone us-central1-a

# Azure AKS
az aks create --resource-group myResourceGroup --name microservices
```

### 2. Build and Push Images

#### Local Registry (for testing)
```bash
# Build images
docker build -t localhost:5000/backend:latest ./backend
docker build -t localhost:5000/frontend:latest ./frontend

# Push to local registry
docker push localhost:5000/backend:latest
docker push localhost:5000/frontend:latest
```

#### GitHub Container Registry
```bash
# Login
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and tag
docker build -t ghcr.io/USERNAME/backend:latest ./backend
docker build -t ghcr.io/USERNAME/frontend:latest ./frontend

# Push
docker push ghcr.io/USERNAME/backend:latest
docker push ghcr.io/USERNAME/frontend:latest
```

### 3. Update Image References

Edit k8s/backend-deployment.yaml and k8s/frontend-deployment.yaml:
```yaml
image: ghcr.io/USERNAME/backend:latest
image: ghcr.io/USERNAME/frontend:latest
```

### 4. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy configuration
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy services
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml

# Deploy scaling and policies
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/network-policy.yaml
```

### 5. Verify Deployment

```bash
# Check all resources
kubectl get all -n microservices

# Check pod status
kubectl get pods -n microservices -w

# Check logs
kubectl logs -f deployment/backend -n microservices
kubectl logs -f deployment/frontend -n microservices

# Check ingress
kubectl get ingress -n microservices
```

### 6. Configure DNS

#### For Minikube
```bash
# Get minikube IP
minikube ip

# Add to /etc/hosts
echo "$(minikube ip) microservices.local" | sudo tee -a /etc/hosts
```

#### For Kind
```bash
# Add to /etc/hosts
echo "127.0.0.1 microservices.local" | sudo tee -a /etc/hosts
```

#### For Cloud
```bash
# Get LoadBalancer IP
kubectl get ingress -n microservices

# Add to DNS provider or /etc/hosts
```

### 7. Access Application

Open browser: http://microservices.local

## Production Deployment

### 1. Update Secrets

```bash
# Generate secure password
REDIS_PASSWORD=$(openssl rand -base64 32)

# Create secret
kubectl create secret generic redis-secret \
  --from-literal=redis-password=$REDIS_PASSWORD \
  -n microservices
```

### 2. Configure TLS

```bash
# Create TLS secret
kubectl create secret tls microservices-tls \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key \
  -n microservices

# Update ingress
kubectl patch ingress microservices-ingress -n microservices --type=json \
  -p='[{"op": "add", "path": "/spec/tls", "value": [{"hosts": ["microservices.example.com"], "secretName": "microservices-tls"}]}]'
```

### 3. Enable Monitoring

```bash
# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Install Grafana dashboards
kubectl apply -f monitoring/dashboards/
```

### 4. Configure Backups

```bash
# Install Velero for cluster backups
velero install --provider aws --bucket my-backup-bucket

# Create backup schedule
velero schedule create daily-backup --schedule="0 2 * * *"
```

## Rollback Procedures

### Rollback Deployment
```bash
# View rollout history
kubectl rollout history deployment/backend -n microservices

# Rollback to previous version
kubectl rollout undo deployment/backend -n microservices

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=2 -n microservices
```

### Emergency Procedures
```bash
# Scale down
kubectl scale deployment/backend --replicas=0 -n microservices

# Delete problematic pods
kubectl delete pod <pod-name> -n microservices

# Restore from backup
velero restore create --from-backup daily-backup-20240227
```

## Maintenance

### Update Application
```bash
# Build new image
docker build -t ghcr.io/USERNAME/backend:v2.0.0 ./backend

# Update deployment
kubectl set image deployment/backend backend=ghcr.io/USERNAME/backend:v2.0.0 -n microservices

# Monitor rollout
kubectl rollout status deployment/backend -n microservices
```

### Scale Services
```bash
# Manual scaling
kubectl scale deployment/backend --replicas=5 -n microservices

# Update HPA
kubectl patch hpa backend-hpa -n microservices -p '{"spec":{"maxReplicas":20}}'
```

### Clean Up
```bash
# Delete namespace (removes all resources)
kubectl delete namespace microservices

# Delete specific resources
kubectl delete -f k8s/
```
