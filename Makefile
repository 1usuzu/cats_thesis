.PHONY: setup test lint format docker-up docker-up-cpu docker-down docker-pre-pull

setup:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=gateway --cov=orchestrator --cov-report=term-missing

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check .

format:
	ruff format .

docker-up:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

docker-up-cpu:
	docker compose up -d

docker-down:
	docker compose down

docker-pre-pull:
	docker compose pull
