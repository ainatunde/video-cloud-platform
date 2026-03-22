# ─────────────────────────────────────────────────────────────────────────────
# Video Cloud Distribution Platform — Makefile
# ─────────────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
COMPOSE        := docker compose
COMPOSE_DEV    := docker compose -f docker-compose.yml -f docker-compose.dev.yml
KUBECTL        := kubectl

.PHONY: help up down dev build logs ps setup deploy test test-stream health clean \
        k8s-deploy k8s-delete

## help        : Show this help message
help:
	@echo ""
	@echo "  Video Cloud Distribution Platform"
	@echo "  ─────────────────────────────────"
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
	@echo ""

## up          : Start the full production stack (detached)
up:
	@echo "▶  Starting production stack..."
	$(COMPOSE) up -d
	@echo "✔  Stack started. Run 'make ps' to verify services."

## down        : Stop and remove containers (preserves volumes)
down:
	@echo "▶  Stopping stack..."
	$(COMPOSE) down
	@echo "✔  Stack stopped."

## dev         : Start development stack with hot reload
dev:
	@echo "▶  Starting development stack..."
	$(COMPOSE_DEV) up

## build       : Build (or rebuild) all service images
build:
	@echo "▶  Building images..."
	$(COMPOSE) build --pull
	@echo "✔  Build complete."

## logs        : Tail logs for all services (Ctrl-C to stop)
logs:
	$(COMPOSE) logs -f --tail=100

## ps          : Show running service status
ps:
	$(COMPOSE) ps

## setup       : Run first-time setup script
setup:
	@echo "▶  Running setup..."
	@bash scripts/setup.sh
	@echo "✔  Setup complete."

## deploy      : Run production deploy script
deploy:
	@echo "▶  Deploying..."
	@bash scripts/deploy.sh
	@echo "✔  Deploy complete."

## test        : Run unit and integration tests
test:
	@echo "▶  Running tests..."
	@python3 -m pytest tests/ -v
	@echo "✔  Tests complete."

## test-stream : Push a synthetic RTMP test stream via FFmpeg
test-stream:
	@echo "▶  Generating test stream..."
	@bash scripts/generate_test_stream.sh

## health      : Run the platform health check
health:
	@echo "▶  Running health check..."
	@python3 scripts/monitoring/health_check.py

## clean       : Stop stack AND remove all volumes (destructive!)
clean:
	@echo "⚠  This will delete all volumes including stored video and database data."
	@read -p "Continue? [y/N] " ans && [ "$$ans" = "y" ] || exit 1
	$(COMPOSE) down -v --remove-orphans
	@echo "✔  All containers and volumes removed."

## k8s-deploy  : Deploy platform to Kubernetes (kubectl apply)
k8s-deploy:
	@echo "▶  Deploying to Kubernetes..."
	$(KUBECTL) apply -f kubernetes/
	@echo "✔  Kubernetes resources applied."

## k8s-delete  : Remove platform from Kubernetes
k8s-delete:
	@echo "▶  Removing Kubernetes resources..."
	$(KUBECTL) delete -f kubernetes/
	@echo "✔  Kubernetes resources deleted."
