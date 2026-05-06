.PHONY: test coverage lint format typecheck precommit-install precommit production-smoke

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
	cd .. && uv run --project backend pre-commit install --hook-type pre-commit --hook-type pre-push

precommit:
	cd .. && uv run --project backend pre-commit run --all-files

# Simulates the production-clean install + smoke import gates that ship in
# REC-015 (Backend Production Smoke GHA workflow) and REC-019 (the
# pre-push hook). The trap restores the dev venv on exit so a failed
# smoke does not leave the local environment in `--no-dev` state.
# Use directly via `make production-smoke` or via the pre-push hook.
production-smoke:
	@bash -c 'set -e; \
		trap "uv sync --frozen >/dev/null 2>&1" EXIT; \
		echo "→ uv sync --no-dev --frozen"; \
		uv sync --no-dev --frozen; \
		echo "→ smoke import — web entrypoint (create_app)"; \
		uv run python -c "from src.bootstrap.web import create_app; create_app()"; \
		echo "→ smoke import — worker entrypoint (broker)"; \
		uv run python -c "from src.bootstrap.broker import broker"; \
		echo "✓ production-smoke green"'
