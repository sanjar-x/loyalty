"""Integration tests for FavoriteListRepository / FavoriteItemRepository.

Cover the partial-unique-default index, idempotency on UNIQUE conflicts,
and the cross-list batch lookup that powers storefront heart icons.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.favorites.domain.entities import FavoriteItem, FavoriteList
from src.modules.favorites.domain.value_objects import FavoriteTargetType
from src.modules.favorites.infrastructure.repositories.favorite_item_repository import (
    FavoriteItemRepository,
)
from src.modules.favorites.infrastructure.repositories.favorite_list_repository import (
    FavoriteListRepository,
)
from src.modules.identity.domain.value_objects import AccountType, IdentityType
from src.modules.identity.infrastructure.models import IdentityModel

pytestmark = pytest.mark.integration


async def _seed_identity(session: AsyncSession) -> uuid.UUID:
    identity_id = uuid.uuid4()
    session.add(
        IdentityModel(
            id=identity_id,
            primary_auth_method=IdentityType.LOCAL.value,
            account_type=AccountType.CUSTOMER.value,
            is_active=True,
            token_version=1,
        )
    )
    await session.flush()
    return identity_id


async def test_add_and_get_list(db_session: AsyncSession) -> None:
    repo = FavoriteListRepository(db_session)
    identity_id = await _seed_identity(db_session)

    favorite_list = FavoriteList.create_default(identity_id)
    favorite_list.clear_domain_events()
    await repo.add(favorite_list)

    fetched = await repo.get(favorite_list.id)
    assert fetched is not None
    assert fetched.is_default is True
    assert fetched.identity_id == identity_id


async def test_partial_unique_default_index(db_session: AsyncSession) -> None:
    repo = FavoriteListRepository(db_session)
    identity_id = await _seed_identity(db_session)

    first = FavoriteList.create_default(identity_id)
    first.clear_domain_events()
    await repo.add(first)

    second = FavoriteList.create_default(identity_id)
    second.clear_domain_events()
    with pytest.raises(IntegrityError):
        await repo.add(second)


async def test_name_uniqueness_per_identity(db_session: AsyncSession) -> None:
    repo = FavoriteListRepository(db_session)
    identity_id = await _seed_identity(db_session)

    first = FavoriteList.create(identity_id=identity_id, name="Wishlist")
    first.clear_domain_events()
    await repo.add(first)

    second = FavoriteList.create(identity_id=identity_id, name="Wishlist")
    second.clear_domain_events()
    with pytest.raises(IntegrityError):
        await repo.add(second)


async def test_item_unique_per_list(db_session: AsyncSession) -> None:
    list_repo = FavoriteListRepository(db_session)
    item_repo = FavoriteItemRepository(db_session)
    identity_id = await _seed_identity(db_session)

    favorite_list = FavoriteList.create_default(identity_id)
    favorite_list.clear_domain_events()
    await list_repo.add(favorite_list)

    target_id = uuid.uuid4()
    item = FavoriteItem(
        id=uuid.uuid4(),
        list_id=favorite_list.id,
        target_type=FavoriteTargetType.PRODUCT,
        target_id=target_id,
        added_at=datetime.now(UTC),
    )
    await item_repo.add(item)

    duplicate = FavoriteItem(
        id=uuid.uuid4(),
        list_id=favorite_list.id,
        target_type=FavoriteTargetType.PRODUCT,
        target_id=target_id,
        added_at=datetime.now(UTC),
    )
    with pytest.raises(IntegrityError):
        await item_repo.add(duplicate)


async def test_remove_item_idempotent(db_session: AsyncSession) -> None:
    list_repo = FavoriteListRepository(db_session)
    item_repo = FavoriteItemRepository(db_session)
    identity_id = await _seed_identity(db_session)

    favorite_list = FavoriteList.create_default(identity_id)
    favorite_list.clear_domain_events()
    await list_repo.add(favorite_list)

    deleted = await item_repo.remove(
        list_id=favorite_list.id,
        target_type=FavoriteTargetType.PRODUCT,
        target_id=uuid.uuid4(),
    )
    assert deleted is False


async def test_check_batch_default_priority(db_session: AsyncSession) -> None:
    list_repo = FavoriteListRepository(db_session)
    item_repo = FavoriteItemRepository(db_session)
    identity_id = await _seed_identity(db_session)

    default_list = FavoriteList.create_default(identity_id)
    default_list.clear_domain_events()
    await list_repo.add(default_list)

    custom_list = FavoriteList.create(identity_id=identity_id, name="Custom")
    custom_list.clear_domain_events()
    await list_repo.add(custom_list)

    target_id = uuid.uuid4()
    await item_repo.add(
        FavoriteItem(
            id=uuid.uuid4(),
            list_id=custom_list.id,
            target_type=FavoriteTargetType.PRODUCT,
            target_id=target_id,
            added_at=datetime.now(UTC),
        )
    )
    await item_repo.add(
        FavoriteItem(
            id=uuid.uuid4(),
            list_id=default_list.id,
            target_type=FavoriteTargetType.PRODUCT,
            target_id=target_id,
            added_at=datetime.now(UTC),
        )
    )

    mapping = await item_repo.check_batch(
        identity_id=identity_id,
        target_type=FavoriteTargetType.PRODUCT,
        target_ids=[target_id, uuid.uuid4()],
    )
    assert mapping[target_id] == default_list.id
