# Microservices Helm Chart

## Installation

### Install with default values

```bash
helm install microservices ./helm
```

### Install with custom values

```bash
helm install microservices ./helm -f custom-values.yaml
```

### Install in specific namespace

```bash
helm install microservices ./helm --namespace microservices --create-namespace
```

## Configuration

### Common Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace` | Kubernetes namespace | `microservices` |
| `backend.replicaCount` | Number of backend replicas | `2` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.host` | Ingress hostname | `microservices.local` |

### Backend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.image.repository` | Backend image repository | `ghcr.io/your-org/backend` |
| `backend.image.tag` | Backend image tag | `latest` |
| `backend.resources.requests.memory` | Memory request | `128Mi` |
| `backend.resources.limits.memory` | Memory limit | `256Mi` |

### Frontend Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.image.repository` | Frontend image repository | `ghcr.io/your-org/frontend` |
| `frontend.image.tag` | Frontend image tag | `latest` |
| `frontend.resources.requests.memory` | Memory request | `128Mi` |
| `frontend.resources.limits.memory` | Memory limit | `256Mi` |

### Redis Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.password` | Redis password | `redis-secure-password-123` |
| `redis.resources.requests.memory` | Memory request | `128Mi` |
| `redis.resources.limits.memory` | Memory limit | `256Mi` |

## Upgrading

```bash
helm upgrade microservices ./helm
```

## Uninstalling

```bash
helm uninstall microservices
```

## Examples

### Production deployment with custom resources

```yaml
# production-values.yaml
backend:
  replicaCount: 5
  resources:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "512Mi"
      cpu: "1000m"

frontend:
  replicaCount: 5
  resources:
    requests:
      memory: "256Mi"
      cpu: "200m"
    limits:
      memory: "512Mi"
      cpu: "1000m"

ingress:
  host: microservices.example.com
```

```bash
helm install microservices ./helm -f production-values.yaml
```

### Development deployment

```yaml
# dev-values.yaml
backend:
  replicaCount: 1
  autoscaling:
    enabled: false

frontend:
  replicaCount: 1
  autoscaling:
    enabled: false

networkPolicy:
  enabled: false
```

```bash
helm install microservices ./helm -f dev-values.yaml
```
