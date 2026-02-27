.PHONY: help build push deploy clean test

help:
	@echo "Available targets:"
	@echo "  build       - Build Docker images"
	@echo "  push        - Push images to registry"
	@echo "  deploy      - Deploy to Kubernetes"
	@echo "  clean       - Clean up resources"
	@echo "  test        - Run tests"
	@echo "  local       - Run locally with Docker"

build:
	docker build -t backend:latest ./backend
	docker build -t frontend:latest ./frontend

push:
	docker tag backend:latest ghcr.io/$(GITHUB_USER)/backend:latest
	docker tag frontend:latest ghcr.io/$(GITHUB_USER)/frontend:latest
	docker push ghcr.io/$(GITHUB_USER)/backend:latest
	docker push ghcr.io/$(GITHUB_USER)/frontend:latest

deploy:
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

clean:
	kubectl delete namespace microservices

test:
	cd backend && python -m pytest
	cd frontend && python -m pytest

local:
	docker network create microservices-net || true
	docker run -d --name redis --network microservices-net \
		-e REDIS_PASSWORD=redis-secure-password-123 \
		redis:7-alpine redis-server --requirepass redis-secure-password-123
	docker run -d --name backend --network microservices-net \
		-e REDIS_HOST=redis -e REDIS_PORT=6379 \
		-e REDIS_PASSWORD=redis-secure-password-123 \
		-p 5000:5000 backend:latest
	docker run -d --name frontend --network microservices-net \
		-e BACKEND_URL=http://backend:5000 \
		-p 8080:8080 frontend:latest

local-clean:
	docker stop frontend backend redis || true
	docker rm frontend backend redis || true
	docker network rm microservices-net || true
