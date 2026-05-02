# ─── TenderLens Makefile ──────────────────────────────────

.PHONY: up down build test migrate export-audit lint

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

test:
	docker compose exec api pytest tests/ -v

migrate:
	docker compose exec api alembic upgrade head

export-audit:
	@read -p "Enter tender_id: " tid; \
	docker compose exec api python -m services.api.features.audit.exporter --tender-id $$tid

lint:
	docker compose exec api ruff check . && docker compose exec api black --check .

logs:
	docker compose logs -f

shell-api:
	docker compose exec api /bin/bash

shell-db:
	docker compose exec db psql -U tenderlens

redis-cli:
	docker compose exec redis redis-cli
