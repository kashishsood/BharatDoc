# =============================================================
# BharatDoc-VLM — Makefile
# =============================================================
# Targets for install, test, train, eval, serve, report, lint, docker

.PHONY: install test train eval serve report lint docker-up docker-down clean help

# Default python — override with: make install PYTHON=python3.11
PYTHON ?= python
PIP ?= pip

help: ## Show this help message
	@echo "BharatDoc-VLM — Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	$(PIP) install -r requirements.txt
	@echo "✅ Dependencies installed"

test: ## Run all tests with pytest
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-schemas: ## Run schema validation tests only
	$(PYTHON) -m pytest tests/test_schemas.py -v

test-pipeline: ## Run data pipeline tests only
	$(PYTHON) -m pytest tests/test_pipeline.py -v

test-inference: ## Run inference server tests only
	$(PYTHON) -m pytest tests/test_inference.py -v

train: ## Run training pipeline (uses config.yaml)
	$(PYTHON) -m training.train_donut --config training/config.yaml

train-trocr: ## Fine-tune TrOCR for handwritten docs
	$(PYTHON) -m training.train_trocr --config training/config.yaml

train-layoutlm: ## Fine-tune LayoutLMv3 for table docs
	$(PYTHON) -m training.train_layoutlm --config training/config.yaml

train-llava: ## Fine-tune LLaVA for visual QA
	$(PYTHON) -m training.train_llava --config training/config.yaml

eval: ## Run full evaluation suite
	$(PYTHON) -m evaluation.field_level_eval --config training/config.yaml
	$(PYTHON) -m evaluation.document_level_eval --config training/config.yaml
	$(PYTHON) -m evaluation.slice_eval --config training/config.yaml

report: ## Generate PDF benchmark report
	$(PYTHON) -m evaluation.generate_report --run_id latest

serve: ## Start inference server (mock mode)
	$(PYTHON) -m inference.server --mock --port 8001

gateway: ## Start gateway server (mock mode)
	$(PYTHON) -m gateway.gateway --mock --port 8000

serve-all: ## Start gateway + inference (mock mode)
	@echo "Starting inference server on :8001..."
	$(PYTHON) -m inference.server --mock --port 8001 &
	@echo "Starting gateway on :8000..."
	$(PYTHON) -m gateway.gateway --mock --port 8000

benchmark: ## Run inference benchmark (100 seq + 100 concurrent)
	$(PYTHON) -m inference.benchmark --url http://localhost:8001

lint: ## Run linting checks
	$(PYTHON) -m py_compile gateway/gateway.py
	$(PYTHON) -m py_compile router/classifier.py
	$(PYTHON) -m py_compile inference/server.py
	@echo "✅ All modules compile successfully"

synthetic-data: ## Generate synthetic training data
	$(PYTHON) -m data_pipeline.synthetic_gen --count 50 --output data/synthetic/

docker-up: ## Start all services via docker-compose
	docker-compose -f docker/docker-compose.yml up -d --build

docker-down: ## Stop all docker services
	docker-compose -f docker/docker-compose.yml down

clean: ## Remove generated artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov dist build *.egg-info
	@echo "✅ Cleaned"
