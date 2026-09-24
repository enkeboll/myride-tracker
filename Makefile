.PHONY: help install run web test lint format clean

# Python virtual environment binary path
VENV_BIN = .venv/bin
PYTHON = $(VENV_BIN)/python
PYTEST = $(VENV_BIN)/pytest
PRECOMMIT = $(VENV_BIN)/pre-commit
RUFF = $(VENV_BIN)/ruff

help: ## Display available commands
	@echo "MyRide K12 Bus Tracker - Available Makefile Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies and setup git pre-commit hooks
	$(PYTHON) -m pip install -e ".[dev]"
	$(PRECOMMIT) install

run: ## Start MyRide background daemon and Web Dashboard
	$(PYTHON) main.py run

web: ## Start Web Dashboard standalone server at http://localhost:8080
	$(PYTHON) main.py web --port 8080

test: ## Run full automated pytest test suite
	$(PYTEST) -v tests/

lint: ## Run opinionated pre-commit linters and ruff code checks
	$(RUFF) check .
	$(PRECOMMIT) run --all-files

format: ## Automatically format all codebase files with ruff and prettier
	$(RUFF) format .
	$(PRECOMMIT) run prettier --all-files

clean: ## Clean Python cache files, test outputs, and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
