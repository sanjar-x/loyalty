"""Unit tests for ProductAttributeValueRepository (Data Mapper).

Tests the repository's mapper methods (_to_domain, _to_orm) and verifies
that each public method delegates to the correct SQLAlchemy session
operations. Uses AsyncMock for the session -- no database required.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.domain.entities import (
    ProductAttributeValue as DomainProductAttributeValue,
)
from src.modules.catalog.domain.interfaces import IProductAttributeValueRepository
from src.modules.catalog.infrastructure.models import (
    ProductAttributeValueModel as OrmProductAttributeValue,
)
from src.modules.catalog.infrastructure.repositories.product_attribute_value import (
    ProductAttributeValueRepository,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ids() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Generate a consistent set of UUIDs for test fixtures."""
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _make_domain_entity(
    pav_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    attribute_id: uuid.UUID | None = None,
    attribute_value_id: uuid.UUID | None = None,
) -> DomainProductAttributeValue:
    """Build a domain ProductAttributeValue with defaults."""
    return DomainProductAttributeValue(
        id=pav_id or uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        attribute_id=attribute_id or uuid.uuid4(),
        attribute_value_id=attribute_value_id or uuid.uuid4(),
    )


def _make_orm_model(
    pav_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    attribute_id: uuid.UUID | None = None,
    attribute_value_id: uuid.UUID | None = None,
) -> OrmProductAttributeValue:
    """Build an ORM ProductAttributeValueModel with given or random UUIDs."""
    orm = OrmProductAttributeValue()
    orm.id = pav_id or uuid.uuid4()
    orm.product_id = product_id or uuid.uuid4()
    orm.attribute_id = attribute_id or uuid.uuid4()
    orm.attribute_value_id = attribute_value_id or uuid.uuid4()
    return orm


# ---------------------------------------------------------------------------
# Contract compliance
# ---------------------------------------------------------------------------


class TestRepositoryContract:
    """ProductAttributeValueRepository implements the domain interface."""

    def test_implements_interface(self) -> None:
        """Repository is a subclass of IProductAttributeValueRepository."""
        assert issubclass(ProductAttributeValueRepository, IProductAttributeValueRepository)

    def test_has_add_method(self) -> None:
        """Repository exposes an async 'add' method."""
        assert callable(getattr(ProductAttributeValueRepository, "add", None))

    def test_has_get_method(self) -> None:
        """Repository exposes an async 'get' method."""
        assert callable(getattr(ProductAttributeValueRepository, "get", None))

    def test_has_delete_method(self) -> None:
        """Repository exposes an async 'delete' method."""
        assert callable(getattr(ProductAttributeValueRepository, "delete", None))

    def test_has_list_by_product_method(self) -> None:
        """Repository exposes an async 'list_by_product' method."""
        assert callable(getattr(ProductAttributeValueRepository, "list_by_product", None))

    def test_has_exists_method(self) -> None:
        """Repository exposes an async 'exists' method."""
        assert callable(getattr(ProductAttributeValueRepository, "exists", None))


# ---------------------------------------------------------------------------
# Mapper tests: _to_domain / _to_orm
# ---------------------------------------------------------------------------


class TestToDomainMapper:
    """Tests for _to_domain: ORM model -> domain entity."""

    def test_maps_all_fields(self) -> None:
        """All four UUID fields are transferred from ORM to domain entity."""
        pav_id, product_id, attr_id, val_id = _make_ids()
        orm = _make_orm_model(pav_id, product_id, attr_id, val_id)

        repo = ProductAttributeValueRepository(session=AsyncMock())
        domain = repo._to_domain(orm)

        assert domain.id == pav_id
        assert domain.product_id == product_id
        assert domain.attribute_id == attr_id
        assert domain.attribute_value_id == val_id

    def test_returns_domain_entity_type(self) -> None:
        """Return type is a domain ProductAttributeValue, not the ORM model."""
        orm = _make_orm_model()
        repo = ProductAttributeValueRepository(session=AsyncMock())
        domain = repo._to_domain(orm)
        assert isinstance(domain, DomainProductAttributeValue)

    def test_does_not_return_orm_instance(self) -> None:
        """Mapper must not leak ORM objects into the domain layer."""
        orm = _make_orm_model()
        repo = ProductAttributeValueRepository(session=AsyncMock())
        domain = repo._to_domain(orm)
        assert not isinstance(domain, OrmProductAttributeValue)


class TestToOrmMapper:
    """Tests for _to_orm: domain entity -> ORM model."""

    def test_maps_all_fields(self) -> None:
        """All four UUID fields are transferred from domain entity to ORM model."""
        pav_id, product_id, attr_id, val_id = _make_ids()
        domain = _make_domain_entity(pav_id, product_id, attr_id, val_id)

        repo = ProductAttributeValueRepository(session=AsyncMock())
        orm = repo._to_orm(domain)

        assert orm.id == pav_id
        assert orm.product_id == product_id
        assert orm.attribute_id == attr_id
        assert orm.attribute_value_id == val_id

    def test_returns_orm_model_type(self) -> None:
        """Return type is the ORM model, not a domain entity."""
        domain = _make_domain_entity()
        repo = ProductAttributeValueRepository(session=AsyncMock())
        orm = repo._to_orm(domain)
        assert isinstance(orm, OrmProductAttributeValue)

    def test_roundtrip_preserves_data(self) -> None:
        """domain -> ORM -> domain roundtrip preserves all field values."""
        pav_id, product_id, attr_id, val_id = _make_ids()
        original = _make_domain_entity(pav_id, product_id, attr_id, val_id)

        repo = ProductAttributeValueRepository(session=AsyncMock())
        orm = repo._to_orm(original)
        restored = repo._to_domain(orm)

        assert restored.id == original.id
        assert restored.product_id == original.product_id
        assert restored.attribute_id == original.attribute_id
        assert restored.attribute_value_id == original.attribute_value_id


# ---------------------------------------------------------------------------
# Repository method tests (session interactions)
# ---------------------------------------------------------------------------


class TestAdd:
    """Tests for ProductAttributeValueRepository.add()."""

    @pytest.mark.asyncio
    async def test_add_calls_session_add_and_flush(self) -> None:
        """add() calls session.add() with ORM model and flushes."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)
        domain = _make_domain_entity()

        await repo.add(domain)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_returns_domain_entity(self) -> None:
        """add() returns a domain ProductAttributeValue after persistence."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)
        domain = _make_domain_entity()

        result = await repo.add(domain)

        assert isinstance(result, DomainProductAttributeValue)
        assert result.id == domain.id
        assert result.product_id == domain.product_id
        assert result.attribute_id == domain.attribute_id
        assert result.attribute_value_id == domain.attribute_value_id

    @pytest.mark.asyncio
    async def test_add_passes_orm_model_to_session(self) -> None:
        """The object passed to session.add() is an ORM model, not a domain entity."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)
        domain = _make_domain_entity()

        await repo.add(domain)

        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, OrmProductAttributeValue)
        assert added_obj.id == domain.id


class TestGet:
    """Tests for ProductAttributeValueRepository.get()."""

    @pytest.mark.asyncio
    async def test_get_found_returns_domain_entity(self) -> None:
        """get() returns a domain entity when the ORM row exists."""
        pav_id = uuid.uuid4()
        orm = _make_orm_model(pav_id=pav_id)

        session = AsyncMock()
        session.get.return_value = orm
        repo = ProductAttributeValueRepository(session=session)

        result = await repo.get(pav_id)

        assert result is not None
        assert isinstance(result, DomainProductAttributeValue)
        assert result.id == pav_id
        session.get.assert_awaited_once_with(OrmProductAttributeValue, pav_id)

    @pytest.mark.asyncio
    async def test_get_not_found_returns_none(self) -> None:
        """get() returns None when the ORM row does not exist."""
        session = AsyncMock()
        session.get.return_value = None
        repo = ProductAttributeValueRepository(session=session)

        result = await repo.get(uuid.uuid4())

        assert result is None


class TestDelete:
    """Tests for ProductAttributeValueRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_executes_statement(self) -> None:
        """delete() calls session.execute() with a DELETE statement."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)
        pav_id = uuid.uuid4()

        await repo.delete(pav_id)

        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_returns_none(self) -> None:
        """delete() returns None (void operation)."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)

        result = await repo.delete(uuid.uuid4())

        assert result is None


class TestListByProduct:
    """Tests for ProductAttributeValueRepository.list_by_product()."""

    @pytest.mark.asyncio
    async def test_returns_list_of_domain_entities(self) -> None:
        """list_by_product() maps all ORM rows to domain entities."""
        product_id = uuid.uuid4()
        orm1 = _make_orm_model(product_id=product_id)
        orm2 = _make_orm_model(product_id=product_id)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [orm1, orm2]

        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductAttributeValueRepository(session=session)

        result = await repo.list_by_product(product_id)

        assert len(result) == 2
        assert all(isinstance(e, DomainProductAttributeValue) for e in result)
        assert result[0].id == orm1.id
        assert result[1].id == orm2.id

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none_found(self) -> None:
        """list_by_product() returns an empty list for a product with no assignments."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []

        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductAttributeValueRepository(session=session)

        result = await repo.list_by_product(uuid.uuid4())

        assert result == []


class TestExists:
    """Tests for ProductAttributeValueRepository.exists()."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(self) -> None:
        """exists() returns True when a matching row is found."""
        result_mock = MagicMock()
        result_mock.first.return_value = (uuid.uuid4(),)

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductAttributeValueRepository(session=session)

        assert await repo.exists(uuid.uuid4(), uuid.uuid4()) is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(self) -> None:
        """exists() returns False when no matching row is found."""
        result_mock = MagicMock()
        result_mock.first.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductAttributeValueRepository(session=session)

        assert await repo.exists(uuid.uuid4(), uuid.uuid4()) is False

    @pytest.mark.asyncio
    async def test_exists_calls_execute(self) -> None:
        """exists() delegates to session.execute() with a SELECT statement."""
        result_mock = MagicMock()
        result_mock.first.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductAttributeValueRepository(session=session)

        await repo.exists(uuid.uuid4(), uuid.uuid4())

        session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """Tests for repository initialization."""

    def test_stores_session(self) -> None:
        """Repository stores the provided session as _session."""
        session = AsyncMock()
        repo = ProductAttributeValueRepository(session=session)
        assert repo._session is session
