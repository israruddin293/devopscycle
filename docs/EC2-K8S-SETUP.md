# EC2 Kubernetes Cluster Setup Guide

Complete guide to set up Kubernetes on EC2 and configure GitHub Actions for automatic deployment.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                          │
│                    (CI/CD Pipeline)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ kubectl apply
                         │ (via kubeconfig)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS EC2 Instance                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Kubernetes Cluster (k3s/kubeadm)         │    │
│  │                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │    │
│  │  │ Frontend │  │ Backend  │  │  Redis   │        │    │
│  │  └──────────┘  └──────────┘  └──────────┘        │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────┐         │    │
│  │  │      NGINX Ingress Controller        │         │    │
│  │  └──────────────────────────────────────┘         │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- AWS Account
- EC2 instance (t3.medium or larger recommended)
- Ubuntu 22.04 LTS
- At least 4GB RAM, 2 vCPUs
- 20GB+ storage

## Part 1: EC2 Instance Setup

### 1. Launch EC2 Instance

```bash
# Instance specifications:
# - AMI: Ubuntu 22.04 LTS
# - Instance Type: t3.medium (2 vCPU, 4GB RAM)
# - Storage: 20GB gp3
# - Security Group: Open ports 22, 80, 443, 6443
```

### 2. Configure Security Group

Create security group with these inbound rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|--------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | HTTP traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | HTTPS traffic |
| Custom TCP | TCP | 6443 | GitHub IPs | Kubernetes API |
| Custom TCP | TCP | 10250 | Your IP | Kubelet API |

### 3. Connect to EC2

```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Update system
sudo apt update && sudo apt upgrade -y
```

## Part 2: Install Kubernetes (k3s - Recommended)

### Option A: k3s (Lightweight, Recommended)

```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -

# Check status
sudo systemctl status k3s

# Get kubeconfig
sudo cat /etc/rancher/k3s/k3s.yaml

# Make kubectl accessible
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config

# Verify installation
kubectl get nodes
kubectl get pods -A
```

### Option B: kubeadm (Full Kubernetes)

```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Install container runtime (containerd)
sudo apt install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

# Install kubeadm, kubelet, kubectl
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

# Initialize cluster
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

# Setup kubeconfig
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Install CNI (Flannel)
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml

# Remove taint from master (single node cluster)
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```

## Part 3: Install NGINX Ingress Controller

```bash
# Install NGINX Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/baremetal/deploy.yaml

# Wait for ingress controller to be ready
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

# Check ingress controller
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

## Part 4: Install Metrics Server (for HPA)

```bash
# Install metrics server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For k3s, metrics server is already included
# For kubeadm, you may need to add --kubelet-insecure-tls flag
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Verify
kubectl top nodes
```

## Part 5: Configure GitHub Actions Access

### 1. Get Kubeconfig from EC2

```bash
# On EC2 instance
cat ~/.kube/config
```

### 2. Modify Kubeconfig for Remote Access

```bash
# Replace server URL with EC2 public IP
# Change from: server: https://127.0.0.1:6443
# To: server: https://<EC2-PUBLIC-IP>:6443

# For k3s:
sudo sed -i "s/127.0.0.1/<EC2-PUBLIC-IP>/g" /etc/rancher/k3s/k3s.yaml
sudo cat /etc/rancher/k3s/k3s.yaml

# For kubeadm:
sed -i "s/127.0.0.1/<EC2-PUBLIC-IP>/g" ~/.kube/config
cat ~/.kube/config
```

### 3. Encode Kubeconfig for GitHub Secret

```bash
# On your local machine or EC2
cat ~/.kube/config | base64 -w 0

# Copy the output
```

### 4. Add to GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `KUBECONFIG`
5. Value: Paste the base64 encoded kubeconfig
6. Click "Add secret"

## Part 6: Configure Image Pull Access

### Option A: Use GitHub Container Registry (GHCR)

```bash
# Create image pull secret on EC2 K8s cluster
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB-USERNAME> \
  --docker-password=<GITHUB-TOKEN> \
  --docker-email=<YOUR-EMAIL> \
  -n microservices

# Update deployments to use the secret
kubectl patch serviceaccount default -n microservices -p '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'
```

### Option B: Make Images Public

1. Go to GitHub → Packages
2. Select your package
3. Package settings → Change visibility → Public

## Part 7: Deploy Application

### Manual Deployment (First Time)

```bash
# On EC2 instance
git clone <your-repo-url>
cd project

# Update image references in k8s manifests
sed -i "s|your-registry/backend:latest|ghcr.io/<username>/backend:latest|g" k8s/backend-deployment.yaml
sed -i "s|your-registry/frontend:latest|ghcr.io/<username>/frontend:latest|g" k8s/frontend-deployment.yaml

# Deploy
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/network-policy.yaml

# Check deployment
kubectl get pods -n microservices
kubectl get svc -n microservices
kubectl get ingress -n microservices
```

### Automatic Deployment (GitHub Actions)

After setting up KUBECONFIG secret, push to main branch:

```bash
git add .
git commit -m "Deploy to EC2 K8s"
git push origin main
```

The pipeline will automatically:
1. Build Docker images
2. Push to GHCR
3. Deploy to your EC2 Kubernetes cluster

## Part 8: Access Application

### Get Ingress NodePort

```bash
# Get NodePort
kubectl get svc -n ingress-nginx

# Output example:
# NAME                    TYPE       CLUSTER-IP      EXTERNAL-IP   PORT(S)
# ingress-nginx-controller NodePort  10.43.123.45   <none>        80:30080/TCP,443:30443/TCP
```

### Access via Browser

```
http://<EC2-PUBLIC-IP>:30080
```

### Configure DNS (Optional)

1. Add A record in your DNS provider:
   - Name: microservices.yourdomain.com
   - Type: A
   - Value: <EC2-PUBLIC-IP>

2. Update ingress host:
```bash
kubectl edit ingress microservices-ingress -n microservices
# Change host to: microservices.yourdomain.com
```

3. Access: http://microservices.yourdomain.com:30080

## Part 9: Monitoring and Troubleshooting

### Check Cluster Status

```bash
# Nodes
kubectl get nodes

# All resources
kubectl get all -n microservices

# Pods with details
kubectl get pods -n microservices -o wide

# Logs
kubectl logs -f deployment/backend -n microservices
kubectl logs -f deployment/frontend -n microservices

# Events
kubectl get events -n microservices --sort-by='.lastTimestamp'

# Describe resources
kubectl describe pod <pod-name> -n microservices
```

### Common Issues

#### 1. Pods in ImagePullBackOff

```bash
# Check image pull secret
kubectl get secrets -n microservices

# Create if missing
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  -n microservices
```

#### 2. Ingress Not Working

```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress
kubectl describe ingress microservices-ingress -n microservices

# Check service
kubectl get svc -n ingress-nginx
```

#### 3. HPA Not Scaling

```bash
# Check metrics server
kubectl get pods -n kube-system | grep metrics

# Check HPA
kubectl get hpa -n microservices
kubectl describe hpa backend-hpa -n microservices

# Check metrics
kubectl top pods -n microservices
```

## Part 10: Security Hardening

### 1. Restrict API Server Access

```bash
# Update security group to allow only GitHub Actions IPs
# GitHub Actions IP ranges: https://api.github.com/meta
```

### 2. Enable RBAC

```bash
# Create service account for GitHub Actions
kubectl create serviceaccount github-actions -n microservices

# Create role
kubectl create role deployer --verb=get,list,create,update,patch,delete --resource=deployments,services,configmaps,secrets,ingresses -n microservices

# Create role binding
kubectl create rolebinding github-actions-deployer --role=deployer --serviceaccount=microservices:github-actions -n microservices
```

### 3. Enable TLS

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create Let's Encrypt issuer
# See docs/TLS-SETUP.md for details
```

## Part 11: Backup and Disaster Recovery

### Backup Kubernetes Resources

```bash
# Backup all resources
kubectl get all -n microservices -o yaml > backup.yaml

# Backup specific resources
kubectl get configmap,secret,deployment,service,ingress -n microservices -o yaml > backup-$(date +%Y%m%d).yaml
```

### Restore

```bash
kubectl apply -f backup.yaml
```

## Part 12: Cost Optimization

### Use Spot Instances

- Save up to 90% on EC2 costs
- Configure auto-recovery
- Use for non-production environments

### Right-size Instance

```bash
# Monitor resource usage
kubectl top nodes
kubectl top pods -n microservices

# Adjust instance type based on usage
```

### Auto-shutdown (Dev/Test)

```bash
# Create cron job to stop instance at night
# AWS Lambda or CloudWatch Events
```

## Summary Checklist

- [ ] EC2 instance launched and configured
- [ ] Kubernetes installed (k3s or kubeadm)
- [ ] NGINX Ingress Controller installed
- [ ] Metrics Server installed
- [ ] Kubeconfig extracted and encoded
- [ ] KUBECONFIG added to GitHub Secrets
- [ ] Image pull secret created
- [ ] Application deployed successfully
- [ ] Ingress accessible via browser
- [ ] GitHub Actions pipeline tested
- [ ] Monitoring configured
- [ ] Backups configured

## Next Steps

1. Configure TLS certificates
2. Set up monitoring (Prometheus/Grafana)
3. Configure log aggregation
4. Set up alerting
5. Document runbooks
6. Plan disaster recovery

## Support

For issues:
1. Check logs: `kubectl logs -f <pod-name> -n microservices`
2. Check events: `kubectl get events -n microservices`
3. Review GitHub Actions logs
4. Check EC2 instance health
