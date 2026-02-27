# Kubeadm Cluster to GitHub Actions - Quick Setup

Step-by-step guide for connecting your kubeadm Kubernetes cluster on EC2 to GitHub Actions.

## Prerequisites

✅ Kubeadm cluster already running on EC2
✅ GitHub repository with the project
✅ SSH access to EC2 instance

## Step 1: Get Kubeconfig from EC2

SSH into your EC2 instance:

```bash
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

Get your kubeconfig:

```bash
# Kubeconfig is usually here
cat ~/.kube/config

# Or from admin config
sudo cat /etc/kubernetes/admin.conf
```

Copy the entire output.

## Step 2: Modify Kubeconfig for Remote Access

The kubeconfig has `server: https://127.0.0.1:6443` or `server: https://<PRIVATE-IP>:6443`

You need to change it to your EC2 **public IP**.

### Option A: Modify Locally

1. Copy the kubeconfig content to your local machine
2. Save as `ec2-kubeconfig.yaml`
3. Edit the file:

```yaml
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: <CERT-DATA>
    server: https://<EC2-PUBLIC-IP>:6443  # ← Change this line
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: kubernetes-admin
  name: kubernetes-admin@kubernetes
current-context: kubernetes-admin@kubernetes
kind: Config
preferences: {}
users:
- name: kubernetes-admin
  user:
    client-certificate-data: <CLIENT-CERT>
    client-key-data: <CLIENT-KEY>
```

### Option B: Modify on EC2

```bash
# On EC2 instance
cd ~
cp ~/.kube/config kubeconfig-github.yaml

# Replace IP (use your EC2 public IP)
sed -i 's/127.0.0.1/<EC2-PUBLIC-IP>/g' kubeconfig-github.yaml
# OR
sed -i 's/<PRIVATE-IP>/<EC2-PUBLIC-IP>/g' kubeconfig-github.yaml

# Verify the change
cat kubeconfig-github.yaml | grep server
# Should show: server: https://<EC2-PUBLIC-IP>:6443
```

## Step 3: Configure EC2 Security Group

Allow GitHub Actions to access Kubernetes API (port 6443):

### In AWS Console:

1. Go to EC2 → Security Groups
2. Select your instance's security group
3. Edit Inbound Rules
4. Add rule:
   - **Type**: Custom TCP
   - **Port**: 6443
   - **Source**: 0.0.0.0/0 (or GitHub Actions IP ranges for better security)
   - **Description**: Kubernetes API for GitHub Actions

### Using AWS CLI:

```bash
aws ec2 authorize-security-group-ingress \
    --group-id <SECURITY-GROUP-ID> \
    --protocol tcp \
    --port 6443 \
    --cidr 0.0.0.0/0
```

## Step 4: Verify API Server is Accessible

On EC2, check if API server is listening on all interfaces:

```bash
# Check API server
sudo netstat -tlnp | grep 6443

# Should show: 0.0.0.0:6443 or :::6443
```

If it shows `127.0.0.1:6443`, you need to reconfigure:

```bash
# Edit kube-apiserver manifest
sudo nano /etc/kubernetes/manifests/kube-apiserver.yaml

# Find the line with --bind-address
# Change to: --bind-address=0.0.0.0

# Or add if not present:
# - --bind-address=0.0.0.0

# Save and exit (Ctrl+X, Y, Enter)

# Wait for API server to restart (30-60 seconds)
kubectl get nodes
```

## Step 5: Test Connection from Local Machine

Before adding to GitHub, test locally:

```bash
# On your local machine
export KUBECONFIG=/path/to/ec2-kubeconfig.yaml

# Test connection
kubectl cluster-info
kubectl get nodes
kubectl get pods -A

# If successful, you're ready for GitHub Actions!
```

### Common Issues:

**Error: x509: certificate is valid for 10.x.x.x, not <EC2-PUBLIC-IP>**

Solution: Add EC2 public IP to API server certificate:

```bash
# On EC2
sudo kubeadm init phase certs apiserver \
  --apiserver-cert-extra-sans=<EC2-PUBLIC-IP>

# Restart API server
sudo systemctl restart kubelet

# Wait 30 seconds
kubectl get nodes
```

**Error: Unable to connect to the server**

Solution: Check security group allows port 6443

## Step 6: Encode Kubeconfig for GitHub

```bash
# On your local machine or EC2
cat ec2-kubeconfig.yaml | base64 -w 0

# This will output a long base64 string
# Copy the entire output
```

## Step 7: Add to GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `KUBECONFIG`
5. Value: Paste the base64 string from Step 6
6. Click **Add secret**

## Step 8: Configure Image Pull Secret (Optional but Recommended)

If using private GitHub Container Registry:

```bash
# On EC2, create namespace first
kubectl create namespace microservices

# Create image pull secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<YOUR-GITHUB-USERNAME> \
  --docker-password=<YOUR-GITHUB-TOKEN> \
  --docker-email=<YOUR-EMAIL> \
  -n microservices

# Verify
kubectl get secrets -n microservices
```

### Generate GitHub Token:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Select scopes: `read:packages`, `write:packages`
4. Copy token

## Step 9: Update Deployment Manifests

Update image references in your manifests:

```bash
# On your local machine
cd project

# Update backend deployment
sed -i 's|your-registry/backend:latest|ghcr.io/<YOUR-GITHUB-USERNAME>/backend:latest|g' k8s/backend-deployment.yaml

# Update frontend deployment
sed -i 's|your-registry/frontend:latest|ghcr.io/<YOUR-GITHUB-USERNAME>/frontend:latest|g' k8s/frontend-deployment.yaml

# Commit changes
git add k8s/
git commit -m "Update image registry"
```

## Step 10: Test GitHub Actions Pipeline

### Option A: Push to Main Branch

```bash
git push origin main
```

### Option B: Test with Manual Trigger

Add to your workflow file:

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:  # ← Add this for manual trigger
```

Then:
1. Go to GitHub → Actions
2. Select your workflow
3. Click "Run workflow"

## Step 11: Monitor Deployment

### In GitHub:

1. Go to **Actions** tab
2. Click on the running workflow
3. Watch the logs in real-time

### On EC2:

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

# Watch pods
kubectl get pods -n microservices -w

# Check deployment status
kubectl rollout status deployment/backend -n microservices
kubectl rollout status deployment/frontend -n microservices

# View logs
kubectl logs -f deployment/backend -n microservices
kubectl logs -f deployment/frontend -n microservices

# Check all resources
kubectl get all -n microservices
```

## Step 12: Access Your Application

### Get Ingress NodePort:

```bash
kubectl get svc -n ingress-nginx

# Output example:
# NAME                       TYPE       PORT(S)
# ingress-nginx-controller   NodePort   80:30080/TCP,443:30443/TCP
```

### Access in Browser:

```
http://<EC2-PUBLIC-IP>:30080
```

## Troubleshooting

### Issue 1: Pipeline fails at "Verify cluster connection"

**Error**: `Unable to connect to the server`

**Check**:
```bash
# 1. Security group allows port 6443
# 2. Kubeconfig has correct public IP
# 3. API server is listening on 0.0.0.0:6443

# On EC2:
sudo netstat -tlnp | grep 6443
```

### Issue 2: Pods in ImagePullBackOff

**Error**: `Failed to pull image`

**Solution**:
```bash
# Option 1: Make images public
# Go to GitHub → Packages → Package settings → Change visibility

# Option 2: Add image pull secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  -n microservices

# Update deployments
kubectl patch serviceaccount default -n microservices \
  -p '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'
```

### Issue 3: Certificate Error

**Error**: `x509: certificate is valid for X, not Y`

**Solution**:
```bash
# On EC2, add your public IP to certificate
sudo kubeadm init phase certs apiserver \
  --apiserver-cert-extra-sans=<EC2-PUBLIC-IP>

# Restart kubelet
sudo systemctl restart kubelet

# Wait 30 seconds and test
kubectl get nodes
```

### Issue 4: Ingress Not Working

**Check**:
```bash
# 1. Ingress controller is running
kubectl get pods -n ingress-nginx

# 2. Ingress resource exists
kubectl get ingress -n microservices

# 3. Service endpoints are ready
kubectl get endpoints -n microservices

# 4. Security group allows ports 80 and 443
```

## Complete Verification Checklist

- [ ] Kubeconfig extracted from EC2
- [ ] Server URL changed to EC2 public IP
- [ ] Security group allows port 6443
- [ ] API server listening on 0.0.0.0:6443
- [ ] Local kubectl connection successful
- [ ] Kubeconfig base64 encoded
- [ ] KUBECONFIG added to GitHub Secrets
- [ ] Image pull secret created (if needed)
- [ ] Deployment manifests updated with correct registry
- [ ] GitHub Actions workflow triggered
- [ ] Pods running successfully
- [ ] Application accessible via browser

## Quick Commands Reference

```bash
# Get kubeconfig
cat ~/.kube/config

# Modify server IP
sed -i 's/127.0.0.1/<EC2-PUBLIC-IP>/g' kubeconfig.yaml

# Encode for GitHub
cat kubeconfig.yaml | base64 -w 0

# Test connection
kubectl --kubeconfig=kubeconfig.yaml get nodes

# Watch deployment
kubectl get pods -n microservices -w

# View logs
kubectl logs -f deployment/backend -n microservices

# Get ingress port
kubectl get svc -n ingress-nginx

# Restart deployment
kubectl rollout restart deployment/backend -n microservices
```

## Next Steps

1. ✅ Configure DNS for your domain
2. ✅ Set up TLS certificates (Let's Encrypt)
3. ✅ Configure monitoring (Prometheus/Grafana)
4. ✅ Set up log aggregation
5. ✅ Configure backups
6. ✅ Set up alerts

## Support

If you encounter issues:

1. Check GitHub Actions logs
2. Check pod logs: `kubectl logs <pod-name> -n microservices`
3. Check events: `kubectl get events -n microservices --sort-by='.lastTimestamp'`
4. Verify security groups
5. Test kubeconfig locally first

## Success!

Once everything is working:
- Every push to `main` branch will automatically deploy to your EC2 cluster
- You can monitor deployments in GitHub Actions
- Your application is accessible at `http://<EC2-PUBLIC-IP>:30080`

🎉 Your CI/CD pipeline is now complete!
