"""Logistics-flavoured re-export of the HTTP base client (REC-033).

Promoted to ``src/shared/infrastructure/http/client.py``. Existing
imports
``from src.modules.logistics.infrastructure.providers.base_client import ...``
keep working.
"""

from src.shared.infrastructure.http.client import (
    BaseProviderClient as BaseProviderClient,
)
from src.shared.infrastructure.http.client import (
    ProviderClientConfig as ProviderClientConfig,
)
