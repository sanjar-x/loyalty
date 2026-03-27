
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;

uv run python -m src.modules.identity.management.sync_system_roles

claude --resume 74843687-71a0-4a01-bdb1-a3629425282b
