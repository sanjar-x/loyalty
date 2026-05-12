"""Logistics-flavoured re-export of HTTP provider error types.

Promoted to ``src/shared/infrastructure/http/errors.py`` in REC-033.
Existing imports
``from src.modules.logistics.infrastructure.providers.errors import ...``
keep working.
"""

from shared.infrastructure.http.errors import (
    ProviderAuthError as ProviderAuthError,
)
from shared.infrastructure.http.errors import (
    ProviderHTTPError as ProviderHTTPError,
)
from shared.infrastructure.http.errors import (
    ProviderTimeoutError as ProviderTimeoutError,
)
