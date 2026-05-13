"""Unit-test scope conftest.

Eagerly imports the ORM model registry so every ORM relationship target
(e.g. ``Product → Supplier``) is available by the time SQLAlchemy
configures mappers.  Without this import, tests that instantiate or
touch a mapped class in isolation can fail with
``InvalidRequestError: ... failed to locate a name 'supplier'`` when
pytest-randomly happens to schedule them before a test that already
imported the supplier module.
"""

from __future__ import annotations

# Registering the import side-effect is all we need; we intentionally do
# not re-export anything.
import src.infrastructure.database.registry  # noqa: F401
