"""FastAPI entry point for the ``apps/web`` deployable artefact.

The workspace member ``loyality`` (backend) hosts the actual application
factory under ``src.bootstrap.web:create_app``. This module is a thin
re-export so that Railway's run command can target a stable import path
(``loyality_web.main:app``) independent of the legacy ``backend/main.py``
shim. Deleting this module would shift breaking changes to Railway service
configuration instead of keeping them inside the repository.
"""

from __future__ import annotations

from src.bootstrap.web import create_app

app = create_app()
