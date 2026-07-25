# Mining Super-Agent — Development & Operations Commands
.PHONY: help dev up down restart logs test lint format backup restore deploy clean

# ─── Default ────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Development ────────────────────────────────────────────────
dev: ## Start development environment (hot-reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-detach: ## Start dev environment in background
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

shell: ## Open a shell in the app container
	docker compose exec app bash

db-shell: ## Open PostgreSQL shell
	docker compose exec postgres psql -U mining -d mining

redis-shell: ## Open Redis CLI
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD}

# ─── Production ─────────────────────────────────────────────────
up: ## Start production environment
	docker compose up -d --build

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

restart-app: ## Restart only the app service
	docker compose restart app

logs: ## Tail all logs
	docker compose logs -f

logs-app: ## Tail app logs only
	docker compose logs -f app

logs-db: ## Tail database logs only
	docker compose logs -f postgres

# ─── Database ───────────────────────────────────────────────────
db-migrate: ## Run database migrations
	docker compose exec app python -m src.db.run_migrations

db-init: ## Initialize database with extensions (PostGIS, pgvector)
	docker compose exec postgres psql -U mining -d mining -c "CREATE EXTENSION IF NOT EXISTS postgis;"
	docker compose exec postgres psql -U mining -d mining -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
	docker compose exec postgres psql -U mining -d mining -c "CREATE EXTENSION IF NOT EXISTS pgvector;"
	docker compose exec postgres psql -U mining -d mining -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

db-reset: ## WARNING: Drop and recreate database
	@echo "⚠️  This will DESTROY all data. Press Ctrl+C to abort."
	@sleep 5
	docker compose exec postgres psql -U mining -d mining -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) db-init
	$(MAKE) db-migrate

# ─── Testing ────────────────────────────────────────────────────
test: ## Run all tests
	docker compose exec app python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	docker compose exec app python -m pytest tests/unit/ -v --tb=short

test-integration: ## Run integration tests only
	docker compose exec app python -m pytest tests/integration/ -v --tb=short

test-security: ## Run security tests
	docker compose exec app python -m pytest tests/security/ -v --tb=short

# ─── Code Quality ───────────────────────────────────────────────
lint: ## Run linting (ruff + mypy)
	docker compose exec app ruff check src/ tests/
	docker compose exec app mypy src/ --ignore-missing-imports

format: ## Auto-format code
	docker compose exec app ruff format src/ tests/
	docker compose exec app ruff check --fix src/ tests/

# ─── Backup & Restore ──────────────────────────────────────────
backup: ## Run database backup
	./scripts/backup.sh

restore: ## Restore from backup (usage: make restore BACKUP_FILE=path/to/backup.sql.gz)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make restore BACKUP_FILE=path/to/backup.sql.gz"; \
		exit 1; \
	fi
	./scripts/restore.sh $(BACKUP_FILE)

# ─── Deployment ─────────────────────────────────────────────────
deploy: ## Deploy to production (pull, build, migrate, restart)
	git pull origin main
	docker compose build --no-cache app
	docker compose up -d
	$(MAKE) db-migrate
	docker compose restart app
	@echo "✅ Deployment complete"

deploy-check: ## Verify deployment health
	@echo "Checking services..."
	@docker compose ps
	@echo ""
	@echo "Checking health endpoint..."
	@curl -sf http://localhost:8000/health/detailed || echo "❌ Health check failed"
	@echo ""
	@echo "Checking database..."
	@docker compose exec postgres pg_isready -U mining -d mining

# ─── Cleanup ────────────────────────────────────────────────────
clean: ## Remove stopped containers and dangling images
	docker compose down --remove-orphans
	docker image prune -f

clean-all: ## WARNING: Remove all data volumes
	@echo "⚠️  This will DESTROY all persistent data. Press Ctrl+C to abort."
	@sleep 5
	docker compose down -v --remove-orphans
	docker image prune -f

# ─── Security ───────────────────────────────────────────────────
security-scan: ## Run security scan on dependencies
	docker compose exec app pip-audit
	docker compose exec app safety check

generate-secrets: ## Generate all required secrets
	@echo "=== Generated Secrets ==="
	@echo "JWT_SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
	@echo "JWT_REFRESH_SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
	@echo "API_KEYS_ENCRYPTION_KEY=$$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
	@echo "DB_PASSWORD=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))')"
	@echo "REDIS_PASSWORD=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))')"
	@echo "MINIO_ROOT_PASSWORD=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))')"
	@echo ""
	@echo "Copy these into your .env file"
