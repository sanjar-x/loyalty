
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO public;

uv run alembic -x log_level=debug upgrade head

uv run python -m seed.main                         # all steps (server must be running)
uv run python -m seed.main --step roles,admin,geo  # DB-only (no server needed)
uv run python -m seed.main --step brands,products  # API-only
copilot --resume=4af4c178-1132-453a-aab7-e2096fca675d
copilot --resume=19283663-2d22-4018-bae6-c7014780fddd
copilot --resume=3e9a6835-abfe-4f83-b2d7-91ba17643c8b
__NV_PRIME_RENDER_OFFLOAD=1 __VK_LAYER_NV_optimus=NVIDIA_only __GLX_VENDOR_LIBRARY_NAME=nvidia __GL_SHADER_DISK_CACHE_SKIP_CLEANUP=1 game-performance gamemoderun %command% -nojoy -fullscreen -console -softparticlesdefaultoff -forcenovsync -refresh 165 +fps_max 300 +exec autoexec