.PHONY: setup test lint format docker-up docker-down

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
	docker-compose up -d

docker-down:
	docker-compose down
