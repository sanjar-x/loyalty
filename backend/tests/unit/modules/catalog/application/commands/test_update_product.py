"""Unit tests for UpdateProductHandler command handler.

Covers:
  - UpdateProductCommand dataclass creation and field defaults
  - Happy path: product found, updated, committed
  - Optimistic locking: version mismatch raises ConcurrencyError
  - Slug conflict on update
  - Product not found
  - Selective kwargs forwarding (only provided fields passed to product.update)
  - Slug skips uniqueness check when unchanged
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductHandler,
    UpdateProductResult,
)
from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    ProductNotFoundError,
    ProductSlugConflictError,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    """Build a mock IUnitOfWork that supports async context manager usage."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    return uow


def make_product(
    product_id: uuid.UUID | None = None,
    slug: str = "test-product",
    version: int = 1,
) -> MagicMock:
    """Build a minimal mock Product domain entity."""
    product = MagicMock()
    product.id = product_id or uuid.uuid4()
    product.slug = slug
    product.version = version
    product.update = MagicMock()
    return product


def make_product_repo(product: MagicMock | None = None) -> AsyncMock:
    """Build a mock IProductRepository."""
    repo = AsyncMock()
    repo.get.return_value = product
    repo.check_slug_exists_excluding = AsyncMock(return_value=False)
    repo.update = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# UpdateProductCommand dataclass
# ---------------------------------------------------------------------------


class TestUpdateProductCommand:
    """Tests for UpdateProductCommand construction and field defaults."""

    def test_required_field_only(self) -> None:
        """Command can be created with only product_id — all others default."""
        product_id = uuid.uuid4()
        cmd = UpdateProductCommand(product_id=product_id)

        assert cmd.product_id == product_id
        assert cmd.title_i18n is None
        assert cmd.description_i18n is None
        assert cmd.slug is None
        assert cmd.brand_id is None
        assert cmd.primary_category_id is None
        assert cmd.tags is None
        assert cmd.version is None

    def test_supplier_id_defaults_to_none(self) -> None:
        """supplier_id defaults to None (not provided)."""
        cmd = UpdateProductCommand(product_id=uuid.uuid4())
        assert cmd.supplier_id is None

    def test_country_of_origin_defaults_to_none(self) -> None:
        """country_of_origin defaults to None (not provided)."""
        cmd = UpdateProductCommand(product_id=uuid.uuid4())
        assert cmd.country_of_origin is None

    def test_provided_fields_defaults_to_empty(self) -> None:
        """_provided_fields defaults to an empty frozenset."""
        cmd = UpdateProductCommand(product_id=uuid.uuid4())
        assert cmd._provided_fields == frozenset()

    def test_supplier_id_set_to_none_explicitly(self) -> None:
        """Passing supplier_id=None with _provided_fields means 'clear the field'."""
        cmd = UpdateProductCommand(
            product_id=uuid.uuid4(),
            supplier_id=None,
            _provided_fields=frozenset({"supplier_id"}),
        )
        assert cmd.supplier_id is None
        assert "supplier_id" in cmd._provided_fields

    def test_supplier_id_set_to_uuid(self) -> None:
        """supplier_id can be set to a real UUID."""
        supplier_id = uuid.uuid4()
        cmd = UpdateProductCommand(product_id=uuid.uuid4(), supplier_id=supplier_id,
                _provided_fields=frozenset({"supplier_id"}),
            )
        assert cmd.supplier_id == supplier_id

    def test_country_of_origin_set_to_none_explicitly(self) -> None:
        """Passing country_of_origin=None with _provided_fields means 'clear'."""
        cmd = UpdateProductCommand(
            product_id=uuid.uuid4(),
            country_of_origin=None,
            _provided_fields=frozenset({"country_of_origin"}),
        )
        assert cmd.country_of_origin is None
        assert "country_of_origin" in cmd._provided_fields

    def test_all_fields_provided(self) -> None:
        """Command stores all explicitly provided values correctly."""
        product_id = uuid.uuid4()
        brand_id = uuid.uuid4()
        category_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        cmd = UpdateProductCommand(
            product_id=product_id,
            title_i18n={"en": "New Title"},
            description_i18n={"en": "New Description"},
            slug="new-slug",
            brand_id=brand_id,
            primary_category_id=category_id,
            supplier_id=supplier_id,
            country_of_origin="DE",
            tags=["tag1", "tag2"],
            version=3,
        
                _provided_fields=frozenset({"title_i18n", "description_i18n", "slug", "brand_id", "primary_category_id", "supplier_id", "country_of_origin", "tags"}),
            )

        assert cmd.product_id == product_id
        assert cmd.title_i18n == {"en": "New Title"}
        assert cmd.description_i18n == {"en": "New Description"}
        assert cmd.slug == "new-slug"
        assert cmd.brand_id == brand_id
        assert cmd.primary_category_id == category_id
        assert cmd.supplier_id == supplier_id
        assert cmd.country_of_origin == "DE"
        assert cmd.tags == ["tag1", "tag2"]
        assert cmd.version == 3

    def test_frozen_dataclass_immutable(self) -> None:
        """Command is frozen — mutation raises FrozenInstanceError."""
        cmd = UpdateProductCommand(product_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            cmd.slug = "mutated"  # type: ignore[misc]

    def test_version_zero_stored(self) -> None:
        """version=0 is a valid (if unusual) value and is stored as-is."""
        cmd = UpdateProductCommand(product_id=uuid.uuid4(), version=0)
        assert cmd.version == 0


# ---------------------------------------------------------------------------
# UpdateProductResult dataclass
# ---------------------------------------------------------------------------


class TestUpdateProductResult:
    """Tests for UpdateProductResult construction."""

    def test_result_stores_id(self) -> None:
        """Result wraps the updated product UUID."""
        product_id = uuid.uuid4()
        result = UpdateProductResult(id=product_id)
        assert result.id == product_id

    def test_result_is_frozen(self) -> None:
        """Result is frozen — mutation raises FrozenInstanceError."""
        result = UpdateProductResult(id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            result.id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UpdateProductHandler — happy path
# ---------------------------------------------------------------------------


class TestUpdateProductHandlerHappyPath:
    """Happy-path tests for UpdateProductHandler."""

    async def test_returns_result_with_product_id(self) -> None:
        """Handler returns UpdateProductResult with the product's UUID."""
        product_id = uuid.uuid4()
        product = make_product(product_id=product_id)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        result = await handler.handle(UpdateProductCommand(product_id=product_id))

        assert isinstance(result, UpdateProductResult)
        assert result.id == product_id

    async def test_fetches_product_by_id(self) -> None:
        """Handler calls repo.get with the command's product_id."""
        product_id = uuid.uuid4()
        product = make_product(product_id=product_id)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product_id))

        repo.get.assert_awaited_once_with(product_id)

    async def test_calls_repo_update_and_uow_commit(self) -> None:
        """Handler calls repo.update(product) then uow.commit()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id))

        repo.update.assert_awaited_once_with(product)
        uow.commit.assert_awaited_once()

    async def test_title_i18n_forwarded_to_product_update(self) -> None:
        """When title_i18n is provided, it is forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                title_i18n={"en": "New Title"},
            
                _provided_fields=frozenset({"title_i18n"}),
            )
        )

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("title_i18n") == {"en": "New Title"}

    async def test_description_i18n_forwarded(self) -> None:
        """When description_i18n is provided, it is forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                description_i18n={"en": "New Description"},
            
                _provided_fields=frozenset({"description_i18n"}),
            )
        )

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("description_i18n") == {"en": "New Description"}

    async def test_brand_id_forwarded(self) -> None:
        """When brand_id is provided, it is forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        brand_id = uuid.uuid4()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, brand_id=brand_id,
                _provided_fields=frozenset({"brand_id"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("brand_id") == brand_id

    async def test_tags_forwarded(self) -> None:
        """When tags is provided, it is forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, tags=["tag1", "tag2"],
                _provided_fields=frozenset({"tags"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("tags") == ["tag1", "tag2"]

    async def test_no_version_provided_skips_version_check(self) -> None:
        """version=None means no optimistic lock check — handler proceeds normally."""
        product = make_product(version=5)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        # Should not raise even though we don't match the product version
        result = await handler.handle(UpdateProductCommand(product_id=product.id, version=None))

        assert result.id == product.id
        uow.commit.assert_awaited_once()

    async def test_version_matches_no_error(self) -> None:
        """version matches product.version — handler proceeds normally."""
        product = make_product(version=3)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        result = await handler.handle(UpdateProductCommand(product_id=product.id, version=3))

        assert result.id == product.id
        uow.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# UpdateProductHandler — product not found
# ---------------------------------------------------------------------------


class TestUpdateProductHandlerNotFound:
    """Tests for ProductNotFoundError path."""

    async def test_raises_product_not_found_error(self) -> None:
        """repo.get returns None -> ProductNotFoundError is raised."""
        product_id = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(UpdateProductCommand(product_id=product_id))

    async def test_no_commit_when_not_found(self) -> None:
        """No uow.commit when product is not found."""
        product_id = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(UpdateProductCommand(product_id=product_id))

        uow.commit.assert_not_awaited()

    async def test_no_repo_update_when_not_found(self) -> None:
        """repo.update is never called when product is not found."""
        product_id = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductNotFoundError):
            await handler.handle(UpdateProductCommand(product_id=product_id))

        repo.update.assert_not_awaited()


# ---------------------------------------------------------------------------
# UpdateProductHandler — optimistic locking
# ---------------------------------------------------------------------------


class TestUpdateProductHandlerOptimisticLocking:
    """Tests for ConcurrencyError path (version mismatch)."""

    async def test_raises_concurrency_error_on_version_mismatch(self) -> None:
        """version != product.version raises ConcurrencyError."""
        product = make_product(version=2)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ConcurrencyError):
            await handler.handle(UpdateProductCommand(product_id=product.id, version=1))

    async def test_concurrency_error_contains_entity_type(self) -> None:
        """ConcurrencyError carries entity_type='Product'."""
        product = make_product(version=5)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ConcurrencyError) as exc_info:
            await handler.handle(UpdateProductCommand(product_id=product.id, version=99))

        assert "Product" in str(exc_info.value)

    async def test_no_product_update_on_version_mismatch(self) -> None:
        """product.update() is not called when version check fails."""
        product = make_product(version=2)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ConcurrencyError):
            await handler.handle(UpdateProductCommand(product_id=product.id, version=1))

        product.update.assert_not_called()

    async def test_no_commit_on_version_mismatch(self) -> None:
        """uow.commit is not called when version check fails."""
        product = make_product(version=2)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ConcurrencyError):
            await handler.handle(UpdateProductCommand(product_id=product.id, version=1))

        uow.commit.assert_not_awaited()

    async def test_version_zero_raises_when_product_version_is_one(self) -> None:
        """version=0 never matches a real product (versions start at 1) -> ConcurrencyError."""
        product = make_product(version=1)
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ConcurrencyError):
            await handler.handle(UpdateProductCommand(product_id=product.id, version=0))


# ---------------------------------------------------------------------------
# UpdateProductHandler — slug conflict
# ---------------------------------------------------------------------------


class TestUpdateProductHandlerSlugConflict:
    """Tests for ProductSlugConflictError path."""

    async def test_raises_slug_conflict_when_slug_taken(self) -> None:
        """Slug is changing and already taken -> ProductSlugConflictError."""
        product = make_product(slug="current-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = True
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(UpdateProductCommand(product_id=product.id, slug="taken-slug",
                _provided_fields=frozenset({"slug"}),
            ))

    async def test_slug_conflict_check_uses_correct_args(self) -> None:
        """Slug conflict check passes new slug and product_id as exclude_id."""
        product_id = uuid.uuid4()
        product = make_product(product_id=product_id, slug="old-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = True
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(UpdateProductCommand(product_id=product_id, slug="new-slug",
                _provided_fields=frozenset({"slug"}),
            ))

        repo.check_slug_exists_excluding.assert_awaited_once_with("new-slug", product_id)

    async def test_no_product_update_on_slug_conflict(self) -> None:
        """product.update() is not called when slug conflict is detected."""
        product = make_product(slug="old-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = True
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(UpdateProductCommand(product_id=product.id, slug="taken-slug",
                _provided_fields=frozenset({"slug"}),
            ))

        product.update.assert_not_called()

    async def test_no_commit_on_slug_conflict(self) -> None:
        """uow.commit is not called when slug conflict is detected."""
        product = make_product(slug="old-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = True
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(UpdateProductCommand(product_id=product.id, slug="taken-slug",
                _provided_fields=frozenset({"slug"}),
            ))

        uow.commit.assert_not_awaited()

    async def test_same_slug_skips_uniqueness_check(self) -> None:
        """When slug matches current product.slug, no conflict check is performed."""
        product = make_product(slug="same-slug")
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, slug="same-slug",
                _provided_fields=frozenset({"slug"}),
            ))

        repo.check_slug_exists_excluding.assert_not_awaited()
        uow.commit.assert_awaited_once()

    async def test_no_slug_provided_skips_uniqueness_check(self) -> None:
        """When slug is None (not provided), no conflict check is performed."""
        product = make_product(slug="current-slug")
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, slug=None,
                _provided_fields=frozenset({"slug"}),
            ))

        repo.check_slug_exists_excluding.assert_not_awaited()
        uow.commit.assert_awaited_once()

    async def test_different_slug_triggers_uniqueness_check(self) -> None:
        """When slug differs from current, conflict check is performed."""
        product = make_product(slug="old-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = False
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, slug="new-slug",
                _provided_fields=frozenset({"slug"}),
            ))

        repo.check_slug_exists_excluding.assert_awaited_once()
        uow.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# UpdateProductHandler — provided fields forwarding
# ---------------------------------------------------------------------------


class TestUpdateProductHandlerProvidedFields:
    """Tests for conditional kwargs forwarding via _provided_fields."""

    async def test_no_fields_provided_calls_update_with_empty_kwargs(self) -> None:
        """When no optional fields are provided, product.update() called with no kwargs."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id))

        product.update.assert_called_once_with()

    async def test_supplier_id_not_in_provided_not_forwarded(self) -> None:
        """supplier_id not in _provided_fields is NOT included in kwargs."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id))

        call_kwargs = product.update.call_args.kwargs
        assert "supplier_id" not in call_kwargs

    async def test_supplier_id_none_is_forwarded(self) -> None:
        """supplier_id=None (explicit clear) IS forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, supplier_id=None,
                _provided_fields=frozenset({"supplier_id"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert "supplier_id" in call_kwargs
        assert call_kwargs["supplier_id"] is None

    async def test_supplier_id_uuid_is_forwarded(self) -> None:
        """supplier_id=<UUID> IS forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()
        supplier_id = uuid.uuid4()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, supplier_id=supplier_id,
                _provided_fields=frozenset({"supplier_id"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("supplier_id") == supplier_id

    async def test_country_of_origin_not_in_provided_not_forwarded(self) -> None:
        """country_of_origin not in _provided_fields is NOT included in kwargs."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id))

        call_kwargs = product.update.call_args.kwargs
        assert "country_of_origin" not in call_kwargs

    async def test_country_of_origin_none_is_forwarded(self) -> None:
        """country_of_origin=None (explicit clear) IS forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, country_of_origin=None,
                _provided_fields=frozenset({"country_of_origin"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert "country_of_origin" in call_kwargs
        assert call_kwargs["country_of_origin"] is None

    async def test_country_of_origin_value_is_forwarded(self) -> None:
        """country_of_origin='DE' IS forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id, country_of_origin="DE",
                _provided_fields=frozenset({"country_of_origin"}),
            ))

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get("country_of_origin") == "DE"

    async def test_none_scalar_fields_not_forwarded(self) -> None:
        """title_i18n, description_i18n, slug, brand_id, etc. at None are not forwarded."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(UpdateProductCommand(product_id=product.id))

        call_kwargs = product.update.call_args.kwargs
        for field in (
            "title_i18n",
            "description_i18n",
            "slug",
            "brand_id",
            "primary_category_id",
            "tags",
        ):
            assert field not in call_kwargs, f"Unexpected field in kwargs: {field}"

    async def test_multiple_fields_forwarded_together(self) -> None:
        """Multiple provided fields are all forwarded in a single product.update() call."""
        product = make_product(slug="old-slug")
        repo = make_product_repo(product=product)
        repo.check_slug_exists_excluding.return_value = False
        uow = make_uow()
        brand_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                title_i18n={"en": "Title"},
                slug="new-slug",
                brand_id=brand_id,
                supplier_id=supplier_id,
                country_of_origin="US",
            
                _provided_fields=frozenset({"title_i18n", "slug", "brand_id", "supplier_id", "country_of_origin"}),
            )
        )

        product.update.assert_called_once()
        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs["title_i18n"] == {"en": "Title"}
        assert call_kwargs["slug"] == "new-slug"
        assert call_kwargs["brand_id"] == brand_id
        assert call_kwargs["supplier_id"] == supplier_id
        assert call_kwargs["country_of_origin"] == "US"
        # Not provided fields must NOT appear
        assert "description_i18n" not in call_kwargs
        assert "tags" not in call_kwargs

    @pytest.mark.parametrize(
        "field_name,field_value",
        [
            ("title_i18n", {"en": "Title"}),
            ("description_i18n", {"en": "Desc"}),
            ("brand_id", uuid.uuid4()),
            ("primary_category_id", uuid.uuid4()),
            ("tags", ["a", "b"]),
        ],
    )
    async def test_individual_optional_scalar_field_forwarded(
        self, field_name: str, field_value: object
    ) -> None:
        """Each optional scalar field, when provided, is forwarded to product.update()."""
        product = make_product()
        repo = make_product_repo(product=product)
        uow = make_uow()

        handler = UpdateProductHandler(product_repo=repo, uow=uow)
        await handler.handle(
            UpdateProductCommand(
                product_id=product.id,
                _provided_fields=frozenset({field_name}),
                **{field_name: field_value},
            )
        )

        call_kwargs = product.update.call_args.kwargs
        assert call_kwargs.get(field_name) == field_value
