.PHONY: up up-dev down build logs test test-unit test-integration test-api test-e2e \
        lint format migrate seed benchmark health-check ps clean

up: ## Start the full stack
	docker compose up --build

up-dev: ## Start with hot-reload dev overrides
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down: ## Stop and remove containers
	docker compose down

build: ## Build all images without starting
	docker compose build

logs: ## Tail logs for all services
	docker compose logs -f

ps: ## Show running services
	docker compose ps

migrate: ## Run Alembic migrations against the running Postgres container
	docker compose exec backend alembic upgrade head

seed: ## Generate and index a development dataset (10k docs)
	docker compose exec backend python scripts/seed_data.py --count 10000

seed-1m: ## Generate and index 1,000,000 documents
	docker compose exec backend python scripts/seed_data.py --count 1000000 --seed 42

benchmark: ## Run the search performance benchmark against the running stack
	docker compose exec backend python scripts/benchmark.py

health-check: ## Check the health of all dependencies
	docker compose exec backend python scripts/health_check.py

test: ## Run backend unit + integration + API tests (no external services needed)
	cd backend && python -m pytest tests/unit tests/integration tests/api -v

test-unit:
	cd backend && python -m pytest tests/unit -v

test-integration:
	cd backend && python -m pytest tests/integration -v

test-api:
	cd backend && python -m pytest tests/api -v

test-e2e: ## Requires the full stack running via `make up`
	cd frontend && npx playwright test

lint: ## Lint backend and frontend
	cd backend && ruff check app tests
	cd frontend && npm run lint

format:
	cd backend && ruff format app tests
	cd frontend && npm run format

clean: ## Remove containers, volumes, and build artifacts
	docker compose down -v
	rm -rf backend/.pytest_cache backend/__pycache__ frontend/dist frontend/node_modules
