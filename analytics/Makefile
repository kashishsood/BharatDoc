# BharatDoc Analytics Service - Makefile

.PHONY: help install run dev test seed clean docker-build docker-up docker-down

help: ## Show this help message
	@echo "BharatDoc Analytics Service - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

run: ## Run the analytics service
	uvicorn main:app --host 0.0.0.0 --port 8002

dev: ## Run in development mode with auto-reload
	uvicorn main:app --host 0.0.0.0 --port 8002 --reload

test: ## Run API tests
	python test_api.py

seed: ## Seed database with test data (500 logs)
	python seed_data.py 500

seed-large: ## Seed database with large test data (2000 logs)
	python seed_data.py 2000

example: ## Run integration example
	python example_integration.py

clean: ## Clean up Python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"

docker-build: ## Build Docker image
	docker build -t bharatdoc-analytics:latest .

docker-up: ## Start analytics service with docker-compose
	cd .. && docker-compose -f docker/docker-compose.yml up -d analytics postgres

docker-down: ## Stop analytics service
	cd .. && docker-compose -f docker/docker-compose.yml down

docker-logs: ## View analytics service logs
	cd .. && docker-compose -f docker/docker-compose.yml logs -f analytics

docker-shell: ## Open shell in analytics container
	cd .. && docker-compose -f docker/docker-compose.yml exec analytics /bin/bash

db-shell: ## Open PostgreSQL shell
	cd .. && docker-compose -f docker/docker-compose.yml exec postgres psql -U bharatdoc -d bharatdoc

db-reset: ## Reset database (WARNING: deletes all data)
	cd .. && docker-compose -f docker/docker-compose.yml exec postgres psql -U bharatdoc -d bharatdoc -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	cd .. && docker-compose -f docker/docker-compose.yml exec postgres psql -U bharatdoc -d bharatdoc -f /docker-entrypoint-initdb.d/01-schema.sql
	@echo "✅ Database reset complete"
