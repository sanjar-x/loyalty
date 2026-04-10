
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;

uv run alembic -x log_level=debug upgrade head

uv run python -m seed.main                         # all steps (server must be running)
uv run python -m seed.main --step roles,admin,geo  # DB-only (no server needed)
uv run python -m seed.main --step brands,products  # API-only
