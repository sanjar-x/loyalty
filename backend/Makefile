.PHONY: test coverage lint format typecheck precommit-install precommit

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-e2e:
	uv run pytest tests/e2e/ -v

test-architecture:
	uv run pytest tests/architecture/ -v

coverage:
	uv run pytest tests/ --cov=project --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run ty check

precommit-install:
	cd .. && uv run --project backend pre-commit install

precommit:
	cd .. && uv run --project backend pre-commit run --all-files
