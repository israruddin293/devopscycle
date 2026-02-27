# GitHub Actions to EC2 Kubernetes Deployment

Quick reference guide for deploying from GitHub Actions to EC2 Kubernetes cluster.

## Quick Setup (5 Steps)

### Step 1: Get Kubeconfig from EC2

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-IP>

# For k3s
sudo cat /etc/rancher/k3s/k3s.yaml

# For kubeadm
cat ~/.kube/config
```

### Step 2: Modify Server URL

Replace `127.0.0.1` with your EC2 public IP:

```yaml
# Before
server: https://127.0.0.1:6443

# After
server: https://<EC2-PUBLIC-IP>:6443
```

### Step 3: Encode Kubeconfig

```bash
# On your local machine
cat modified-kubeconfig.yaml | base64 -w 0
```

### Step 4: Add GitHub Secret

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `KUBECONFIG`
4. Value: Paste base64 encoded kubeconfig
5. Save

### Step 5: Update Image Registry

In your workflow file, ensure images point to your registry:

```yaml
env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ${{ github.repository }}/backend
  FRONTEND_IMAGE: ${{ github.repository }}/frontend
```

## Security Group Configuration

Allow GitHub Actions to access your EC2 Kubernetes API:

```bash
# Get GitHub Actions IP ranges
curl https://api.github.com/meta | jq -r '.actions[]'

# Add to EC2 Security Group:
# Type: Custom TCP
# Port: 6443
# Source: GitHub Actions IP ranges (or 0.0.0.0/0 for testing)
```

## Image Pull Configuration

### Option 1: Public Images (Easiest)

Make your GHCR packages public:
1. Go to GitHub → Packages
2. Select package → Settings
3. Change visibility to Public

### Option 2: Image Pull Secret

```bash
# On EC2 cluster
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=<GITHUB-USERNAME> \
  --docker-password=<GITHUB-TOKEN> \
  --docker-email=<EMAIL> \
  -n microservices

# Add to deployments
kubectl patch serviceaccount default -n microservices \
  -p '{"imagePullSecrets": [{"name": "ghcr-secret"}]}'
```

## Workflow Explanation

```yaml
deploy:
  name: Deploy to Kubernetes
  runs-on: ubuntu-latest
  needs: build-and-push
  if: github.ref == 'refs/heads/main'
  
  steps:
  - name: Checkout code
    uses: actions/checkout@v4

  - name: Set up kubectl
    uses: azure/setup-kubectl@v3
    with:
      version: 'latest'

  # Decode and configure kubeconfig
  - name: Configure kubectl
    run: |
      mkdir -p $HOME/.kube
      echo "${{ secrets.KUBECONFIG }}" | base64 -d > $HOME/.kube/config
      chmod 600 $HOME/.kube/config

  # Verify connection to EC2 cluster
  - name: Verify cluster connection
    run: |
      kubectl cluster-info
      kubectl get nodes

  # Update image references
  - name: Update image tags in manifests
    run: |
      sed -i "s|your-registry/backend:latest|${{ env.REGISTRY }}/${{ env.BACKEND_IMAGE }}:latest|g" k8s/backend-deployment.yaml
      sed -i "s|your-registry/frontend:latest|${{ env.REGISTRY }}/${{ env.FRONTEND_IMAGE }}:latest|g" k8s/frontend-deployment.yaml

  # Deploy to EC2 K8s cluster
  - name: Deploy to Kubernetes
    run: |
      kubectl apply -f k8s/namespace.yaml --validate=false
      kubectl apply -f k8s/configmap.yaml --validate=false
      kubectl apply -f k8s/secret.yaml --validate=false
      kubectl apply -f k8s/redis-deployment.yaml --validate=false
      kubectl apply -f k8s/backend-deployment.yaml --validate=false
      kubectl apply -f k8s/frontend-deployment.yaml --validate=false
      kubectl apply -f k8s/ingress.yaml --validate=false
      kubectl apply -f k8s/hpa.yaml --validate=false
      kubectl apply -f k8s/pdb.yaml --validate=false
      kubectl apply -f k8s/network-policy.yaml --validate=false

  # Wait for deployment to complete
  - name: Wait for deployment
    run: |
      kubectl rollout status deployment/backend -n microservices --timeout=5m
      kubectl rollout status deployment/frontend -n microservices --timeout=5m

  # Verify deployment
  - name: Verify deployment
    run: |
      kubectl get pods -n microservices
      kubectl get svc -n microservices
      kubectl get ingress -n microservices
```

## Testing the Pipeline

### 1. Test Locally First

```bash
# On your local machine with kubeconfig configured
kubectl apply -f k8s/namespace.yaml --validate=false
kubectl get namespaces
```

### 2. Test Connection from GitHub Actions

Add a test job:

```yaml
test-connection:
  runs-on: ubuntu-latest
  steps:
  - name: Configure kubectl
    run: |
      mkdir -p $HOME/.kube
      echo "${{ secrets.KUBECONFIG }}" | base64 -d > $HOME/.kube/config
      chmod 600 $HOME/.kube/config
  
  - name: Test connection
    run: |
      kubectl cluster-info
      kubectl get nodes
```

### 3. Deploy

```bash
git add .
git commit -m "Test EC2 deployment"
git push origin main
```

## Troubleshooting

### Error: Unable to connect to the server

**Problem**: GitHub Actions can't reach EC2 Kubernetes API

**Solutions**:
1. Check EC2 security group allows port 6443
2. Verify EC2 public IP in kubeconfig
3. Ensure Kubernetes API is listening on 0.0.0.0:6443

```bash
# On EC2, check API server
sudo netstat -tlnp | grep 6443

# For k3s, ensure it's listening on all interfaces
sudo systemctl edit k3s
# Add: --bind-address=0.0.0.0
```

### Error: x509 certificate is valid for 127.0.0.1, not <EC2-IP>

**Problem**: Kubernetes certificate doesn't include EC2 public IP

**Solution for k3s**:
```bash
# Reinstall k3s with public IP
curl -sfL https://get.k3s.io | sh -s - --tls-san <EC2-PUBLIC-IP>
```

**Solution for kubeadm**:
```bash
# Add SANs to certificate
sudo kubeadm init phase certs apiserver --apiserver-cert-extra-sans=<EC2-PUBLIC-IP>
```

### Error: ImagePullBackOff

**Problem**: Can't pull images from GHCR

**Solutions**:
1. Make images public
2. Create image pull secret (see above)
3. Verify image names are correct

### Error: Forbidden: User cannot create resource

**Problem**: RBAC permissions issue

**Solution**:
```bash
# Use admin kubeconfig
# Or create proper RBAC role (see EC2-K8S-SETUP.md)
```

## Monitoring Deployments

### View Pipeline Logs

```bash
# Using GitHub CLI
gh run list
gh run view <run-id> --log
gh run watch
```

### View Kubernetes Logs

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@<EC2-IP>

# Check pods
kubectl get pods -n microservices

# View logs
kubectl logs -f deployment/backend -n microservices
kubectl logs -f deployment/frontend -n microservices

# Check events
kubectl get events -n microservices --sort-by='.lastTimestamp'
```

## Best Practices

1. **Use Separate Environments**
   - Dev: Deploy on every push
   - Prod: Deploy on tags only

2. **Implement Approval Gates**
   ```yaml
   environment:
     name: production
     url: http://<EC2-IP>:30080
   ```

3. **Use Secrets for Sensitive Data**
   - Never commit kubeconfig
   - Use GitHub Secrets
   - Rotate credentials regularly

4. **Monitor Deployments**
   - Set up alerts
   - Monitor resource usage
   - Track deployment frequency

5. **Implement Rollback**
   ```yaml
   - name: Rollback on failure
     if: failure()
     run: |
       kubectl rollout undo deployment/backend -n microservices
       kubectl rollout undo deployment/frontend -n microservices
   ```

## Complete Example Workflow

See `.github/workflows/ci-cd.yaml` for the complete working example.

## Additional Resources

- [EC2 K8s Setup Guide](EC2-K8S-SETUP.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [k3s Documentation](https://docs.k3s.io/)
