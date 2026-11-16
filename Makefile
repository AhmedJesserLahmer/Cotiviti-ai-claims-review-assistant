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
API_DIR := services/claims-api

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
build: check-memory ## Build one service image (SERVICE=backend|frontend), or all, sequentially
	$(COMPOSE) build --parallel 1 $(SERVICE)

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
test: ## Run backend unit tests
	cd $(API_DIR) && $(PYTHON) -m pytest -q

.PHONY: test-ai
test-ai: ## Run only the AI reliability layer tests (no ML or DB needed)
	cd $(API_DIR) && $(PYTHON) -m pytest -q tests/ai

.PHONY: lint
lint: ## Lint python code with ruff
	cd $(API_DIR) && $(PYTHON) -m ruff check .
