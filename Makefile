# Developer entrypoints for the monorepo.
#
# Builds are deliberately sequential and one service at a time: this project is
# often developed on laptops with limited RAM, and parallel image builds have
# caused out-of-memory kills. Use `make build SERVICE=<name>` to rebuild only
# what changed.

SHELL := /bin/bash
COMPOSE := COMPOSE_PARALLEL_LIMIT=1 docker compose
SERVICE ?=
MIN_FREE_MB ?= 4000
PYTHON ?= python3
PY_PACKAGES := libs/python/claims-common services/ml-service services/ai-agent services/claims-api

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.PHONY: check-memory
check-memory: ## Refuse heavy jobs when available RAM is below MIN_FREE_MB
	@avail=$$(free -m | awk 'NR==2 {print $$7}'); \
	if [ -n "$$avail" ] && [ "$$avail" -lt "$(MIN_FREE_MB)" ]; then \
		echo "Only $${avail} MiB available (< $(MIN_FREE_MB)). Close something first."; exit 1; \
	fi; echo "Memory OK: $${avail:-unknown} MiB available"

.PHONY: env
env: ## Create a local .env from .env.example if it does not exist
	@test -f .env || (cp .env.example .env && echo "Created .env, now set GROQ_API_KEY")

.PHONY: build
build: check-memory ## Build one service image (SERVICE=claims-api|ai-agent|ml-service|frontend), or all, sequentially
	$(COMPOSE) build --parallel 1 $(SERVICE)

.PHONY: k8s-local
k8s-local: ## Build images one by one, load into kind and install the Helm chart
	infra/k8s/scripts/deploy-local.sh $(SERVICE)

.PHONY: helm-lint
helm-lint: ## Lint the Helm chart with every environment's values
	@for env in dev staging prod; do helm lint infra/helm/claims-review -f infra/helm/claims-review/values-$$env.yaml; done

.PHONY: up
up: ## Start the stack in the background
	$(COMPOSE) up -d $(SERVICE)

.PHONY: down
down: ## Stop the stack
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow logs (SERVICE=... to filter)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

.PHONY: ps
ps: ## Show running services
	$(COMPOSE) ps

.PHONY: test
test: ## Run unit tests of every python package
	@set -e; for pkg in $(PY_PACKAGES); do echo "== $$pkg"; (cd $$pkg && $(PYTHON) -m pytest -q); done

.PHONY: test-ai
test-ai: ## Run only the AI reliability layer tests (no ML or DB needed)
	cd services/ai-agent && $(PYTHON) -m pytest -q tests/ai

.PHONY: eval
eval: ## Run the AI evaluation gate (scripted + rule-engine modes)
	cd services/ai-agent && PYTHONPATH=../../libs/python/claims-common/src $(PYTHON) -m evals.run_eval --mode scripted --min-accuracy 0.95 --max-unsafe 0
	cd services/ai-agent && PYTHONPATH=../../libs/python/claims-common/src $(PYTHON) -m evals.run_eval --mode rules --min-accuracy 0.9 --max-unsafe 0

.PHONY: train
train: ## Generate synthetic data and train a new model version locally
	cd services/ml-service && $(PYTHON) -m data_gen.generate_data && $(PYTHON) -m ml.train_models

.PHONY: lint
lint: ## Lint python code with ruff (config: ruff.toml)
	$(PYTHON) -m ruff check libs/python services
