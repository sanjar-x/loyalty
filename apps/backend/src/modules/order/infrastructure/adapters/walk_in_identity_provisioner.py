"""ACL adapter: order → identity + user.

The only file in the order module allowed to import identity / user
ORM — whitelisted in ``tests/architecture/test_boundaries.py`` as
``("order","identity")`` and ``("order","user")``. Used exclusively by
:class:`AdminCreateWalkInOrderHandler` to provision a fresh Identity +
Customer for a walk-in customer (someone the admin is taking an order
for who has never used the system before).

The walk-in identity:

* gets ``primary_auth_method=WALK_IN`` and stays ``is_active=True``;
* has no LocalCredentials and no LinkedAccount — login is impossible
  until a future self-service activation flow attaches credentials;
* shares its primary key with a Customer row (1:1 invariant) carrying
  the inline profile data the admin captured.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.entities import Identity
from src.modules.identity.domain.value_objects import (
    AccountType,
    PrimaryAuthMethod,
)
from src.modules.identity.infrastructure.models import IdentityModel
from src.modules.order.application.ports import (
    IWalkInIdentityProvisioner,
    WalkInCustomerProfileInput,
    WalkInIdentityProvisioned,
)
from src.modules.user.infrastructure.models import CustomerModel


def _split_full_name(full_name: str) -> tuple[str, str]:
    """Split a single ``full_name`` into ``first_name`` / ``last_name``.

    The admin form captures a single string; the underlying Customer
    schema has separate first/last fields. We split on first whitespace
    and put everything after into ``last_name``. Empty / single-word
    names degrade gracefully (last_name="" / first_name="").
    """
    trimmed = full_name.strip()
    if not trimmed:
        return "", ""
    parts = trimmed.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


class WalkInIdentityProvisioner(IWalkInIdentityProvisioner):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def provision(
        self, profile: WalkInCustomerProfileInput
    ) -> WalkInIdentityProvisioned:
        identity = Identity.register(
            identity_type=PrimaryAuthMethod.WALK_IN,
            account_type=AccountType.CUSTOMER,
        )
        first_name, last_name = _split_full_name(profile.full_name)

        identity_row = IdentityModel(
            id=identity.id,
            primary_auth_method=identity.type.value,
            account_type=identity.account_type.value,
            is_active=identity.is_active,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
            token_version=identity.token_version,
        )
        customer_row = CustomerModel(
            id=identity.id,
            profile_email=profile.email,
            first_name=first_name,
            last_name=last_name,
            phone=profile.phone,
            username=None,
            photo_url=None,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )
        self._session.add(identity_row)
        self._session.add(customer_row)
        await self._session.flush()
        return WalkInIdentityProvisioned(identity_id=identity.id)
