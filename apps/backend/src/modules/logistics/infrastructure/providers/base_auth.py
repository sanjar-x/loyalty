"""Logistics-flavoured re-export of HTTP auth managers (REC-033).

Promoted to ``src/shared/infrastructure/http/auth.py``. Existing imports
``from src.modules.logistics.infrastructure.providers.base_auth import ...``
keep working.
"""

from shared.infrastructure.http.auth import (
    BaseAuthManager as BaseAuthManager,
)
from shared.infrastructure.http.auth import (
    BearerTokenAuthManager as BearerTokenAuthManager,
)
from shared.infrastructure.http.auth import (
    DualHeaderAuthManager as DualHeaderAuthManager,
)
from shared.infrastructure.http.auth import (
    OAuth2ClientCredentialsAuthManager as OAuth2ClientCredentialsAuthManager,
)
