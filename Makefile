.PHONY: help dev test lint build up down logs backup restore

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev:  ## Run development server
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:  ## Run tests
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:  ## Run linters
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

build:  ## Build Docker images
	docker compose build

up:  ## Start all services
	docker compose up -d

down:  ## Stop all services
	docker compose down

logs:  ## View logs
	docker compose logs -f app

backup:  ## Run database backup
	./scripts/backup.sh

restore:  ## Restore database (interactive)
	@echo "Usage: ./scripts/restore.sh <backup_file.sql.gz>"

db-init:  ## Initialize database schema
	docker compose exec postgres psql -U mining -d mining -f /docker-entrypoint-initdb.d/001_initial.sql

health:  ## Check service health
	curl -s http://localhost:8000/health/detailed | python -m json.tool
