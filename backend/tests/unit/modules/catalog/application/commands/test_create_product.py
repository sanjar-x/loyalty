"""Unit tests for CreateProductCommand, CreateProductResult, and CreateProductHandler.

Tests cover:
- Command dataclass field defaults and immutability
- Handler happy path: slug available, product created and committed
- Handler slug conflict: raises ProductSlugConflictError, no commit
- Result carries correct product_id
- Empty title_i18n propagates ValueError from Product.create()
- register_aggregate is NOT called (domain events deferred)
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler,
    CreateProductResult,
)
from src.modules.catalog.domain.exceptions import ProductSlugConflictError
from src.modules.catalog.domain.value_objects import ProductStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_uow() -> AsyncMock:
    """Build a fully-mocked IUnitOfWork that works as an async context manager."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.commit = AsyncMock()
    uow.register_aggregate = MagicMock()
    return uow


def make_product_repo(slug_exists: bool = False) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        slug_exists: Return value for check_slug_exists.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.check_slug_exists = AsyncMock(return_value=slug_exists)
    repo.add = AsyncMock()
    return repo


def make_command(
    slug: str = "test-product",
    title_i18n: dict[str, str] | None = None,
    brand_id: uuid.UUID | None = None,
    primary_category_id: uuid.UUID | None = None,
) -> CreateProductCommand:
    """Build a minimal valid CreateProductCommand.

    Args:
        slug: Product URL slug.
        title_i18n: Multilingual title; defaults to {"en": "Test Product"}.
        brand_id: Brand UUID; generates one if None.
        primary_category_id: Category UUID; generates one if None.

    Returns:
        A ready-to-use command instance.
    """
    return CreateProductCommand(
        title_i18n=title_i18n if title_i18n is not None else {"en": "Test Product"},
        slug=slug,
        brand_id=brand_id or uuid.uuid4(),
        primary_category_id=primary_category_id or uuid.uuid4(),
    )


# ---------------------------------------------------------------------------
# CreateProductCommand
# ---------------------------------------------------------------------------


class TestCreateProductCommand:
    """Structural tests for the CreateProductCommand DTO."""

    def test_required_fields_stored_correctly(self) -> None:
        """All four required fields are stored on the dataclass."""
        brand_id = uuid.uuid4()
        category_id = uuid.uuid4()
        cmd = CreateProductCommand(
            title_i18n={"en": "Air Max"},
            slug="air-max",
            brand_id=brand_id,
            primary_category_id=category_id,
        )
        assert cmd.title_i18n == {"en": "Air Max"}
        assert cmd.slug == "air-max"
        assert cmd.brand_id == brand_id
        assert cmd.primary_category_id == category_id

    def test_optional_fields_have_correct_defaults(self) -> None:
        """Optional fields default to empty dict, None, None, and empty list."""
        cmd = make_command()
        assert cmd.description_i18n == {}
        assert cmd.supplier_id is None
        assert cmd.country_of_origin is None
        assert cmd.tags == []

    def test_optional_fields_accept_provided_values(self) -> None:
        """When all optional fields are provided they are stored correctly."""
        supplier_id = uuid.uuid4()
        cmd = CreateProductCommand(
            title_i18n={"en": "Jacket"},
            slug="jacket",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            description_i18n={"en": "A great jacket"},
            supplier_id=supplier_id,
            country_of_origin="DE",
            tags=["outdoor", "jacket"],
        )
        assert cmd.description_i18n == {"en": "A great jacket"}
        assert cmd.supplier_id == supplier_id
        assert cmd.country_of_origin == "DE"
        assert cmd.tags == ["outdoor", "jacket"]

    def test_command_is_frozen(self) -> None:
        """CreateProductCommand is a frozen dataclass — mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.slug = "mutated"  # type: ignore[misc]

    def test_default_factory_instances_are_independent(self) -> None:
        """Two commands with defaults share no mutable state (no aliasing)."""
        cmd1 = make_command(slug="product-1")
        cmd2 = make_command(slug="product-2")
        assert cmd1.description_i18n is not cmd2.description_i18n
        assert cmd1.tags is not cmd2.tags

    def test_multilingual_title_multiple_languages(self) -> None:
        """title_i18n can hold multiple language entries."""
        cmd = CreateProductCommand(
            title_i18n={"en": "Shirt", "uz": "Ko'ylak", "ru": "Рубашка"},
            slug="shirt",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
        )
        assert len(cmd.title_i18n) == 3
        assert cmd.title_i18n["uz"] == "Ko'ylak"


# ---------------------------------------------------------------------------
# CreateProductResult
# ---------------------------------------------------------------------------


class TestCreateProductResult:
    """Structural tests for the CreateProductResult DTO."""

    def test_stores_product_id(self) -> None:
        """product_id is stored as supplied."""
        product_id = uuid.uuid4()
        result = CreateProductResult(product_id=product_id)
        assert result.product_id == product_id

    def test_result_is_frozen(self) -> None:
        """CreateProductResult is a frozen dataclass — mutation must raise."""
        result = CreateProductResult(product_id=uuid.uuid4())
        with pytest.raises(FrozenInstanceError):
            result.product_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CreateProductHandler — happy path
# ---------------------------------------------------------------------------


class TestCreateProductHandlerHappyPath:
    """Handler tests when the slug is available."""

    async def test_returns_result_with_product_id(self) -> None:
        """Handler returns CreateProductResult whose product_id is a UUID."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        result = await handler.handle(make_command())

        assert isinstance(result, CreateProductResult)
        assert isinstance(result.product_id, uuid.UUID)

    async def test_calls_check_slug_exists_with_correct_slug(self) -> None:
        """Handler calls check_slug_exists exactly once with the command's slug."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = make_command(slug="unique-slug")
        await handler.handle(cmd)

        repo.check_slug_exists.assert_awaited_once_with("unique-slug")

    async def test_calls_repo_add_with_product(self) -> None:
        """Handler calls repo.add exactly once with a Product instance."""
        from src.modules.catalog.domain.entities import Product

        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        repo.add.assert_awaited_once()
        added_product = repo.add.call_args[0][0]
        assert isinstance(added_product, Product)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        uow.commit.assert_awaited_once()

    async def test_product_has_draft_status(self) -> None:
        """Product passed to repo.add must be in DRAFT status."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        added_product = repo.add.call_args[0][0]
        assert added_product.status == ProductStatus.DRAFT

    async def test_product_id_matches_result(self) -> None:
        """The product_id in the result matches the id of the persisted product."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        result = await handler.handle(make_command())

        added_product = repo.add.call_args[0][0]
        assert result.product_id == added_product.id

    async def test_product_fields_match_command(self) -> None:
        """Fields on the created Product must mirror all command fields."""
        brand_id = uuid.uuid4()
        category_id = uuid.uuid4()
        supplier_id = uuid.uuid4()

        cmd = CreateProductCommand(
            title_i18n={"en": "Sneakers"},
            slug="sneakers",
            brand_id=brand_id,
            primary_category_id=category_id,
            description_i18n={"en": "Cool sneakers"},
            supplier_id=supplier_id,
            country_of_origin="US",
            tags=["shoes", "sport"],
        )

        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.slug == "sneakers"
        assert product.title_i18n == {"en": "Sneakers"}
        assert product.brand_id == brand_id
        assert product.primary_category_id == category_id
        assert product.supplier_id == supplier_id
        assert product.country_of_origin == "US"
        assert product.tags == ["shoes", "sport"]

    async def test_no_register_aggregate_called(self) -> None:
        """Handler must NOT call uow.register_aggregate (events deferred)."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        uow.register_aggregate.assert_not_called()

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_default_optional_fields_produce_valid_product(self) -> None:
        """Command with all defaults creates a product with empty description and tags."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={"en": "Widget"},
            slug="widget",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
        )
        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.description_i18n == {}
        assert product.supplier_id is None
        assert product.country_of_origin is None
        assert product.tags == []


# ---------------------------------------------------------------------------
# CreateProductHandler — slug conflict
# ---------------------------------------------------------------------------


class TestCreateProductHandlerSlugConflict:
    """Handler tests when the slug is already taken."""

    async def test_raises_product_slug_conflict_error(self) -> None:
        """Handler raises ProductSlugConflictError when slug exists."""
        repo = make_product_repo(slug_exists=True)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(make_command(slug="taken-slug"))

    async def test_error_contains_slug(self) -> None:
        """Raised exception details include the conflicting slug."""
        repo = make_product_repo(slug_exists=True)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError) as exc_info:
            await handler.handle(make_command(slug="taken-slug"))

        # The exception message or details must reference the slug.
        assert "taken-slug" in str(exc_info.value)

    async def test_repo_add_not_called_on_conflict(self) -> None:
        """When slug conflicts, repo.add must not be called."""
        repo = make_product_repo(slug_exists=True)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(make_command(slug="taken-slug"))

        repo.add.assert_not_awaited()

    async def test_commit_not_called_on_conflict(self) -> None:
        """When slug conflicts, uow.commit must not be called."""
        repo = make_product_repo(slug_exists=True)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(make_command(slug="taken-slug"))

        uow.commit.assert_not_awaited()

    async def test_register_aggregate_not_called_on_conflict(self) -> None:
        """When slug conflicts, uow.register_aggregate must not be called."""
        repo = make_product_repo(slug_exists=True)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        with pytest.raises(ProductSlugConflictError):
            await handler.handle(make_command(slug="taken-slug"))

        uow.register_aggregate.assert_not_called()


# ---------------------------------------------------------------------------
# CreateProductHandler — validation / edge cases
# ---------------------------------------------------------------------------


class TestCreateProductHandlerValidation:
    """Handler tests for validation and edge-case inputs."""

    async def test_empty_title_i18n_raises_value_error(self) -> None:
        """Empty title_i18n propagates ValueError from Product.create()."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={},
            slug="no-title",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
        )

        with pytest.raises(ValueError):
            await handler.handle(cmd)

    async def test_empty_title_i18n_does_not_commit(self) -> None:
        """When ValueError is raised for empty title, commit is not called."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={},
            slug="no-title",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
        )

        with pytest.raises(ValueError):
            await handler.handle(cmd)

        uow.commit.assert_not_awaited()

    async def test_empty_description_treated_as_empty_dict(self) -> None:
        """Empty description_i18n (default {}) results in {} on the product."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={"en": "Bag"},
            slug="bag",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            description_i18n={},
        )
        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.description_i18n == {}

    async def test_empty_tags_treated_as_empty_list(self) -> None:
        """Empty tags list (default []) results in [] on the product."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={"en": "Hat"},
            slug="hat",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            tags=[],
        )
        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.tags == []

    async def test_slug_check_called_before_product_create(self) -> None:
        """Slug uniqueness check must happen before Product.create() is invoked.

        Regression for the ordering guaranteed by the plan: check -> create -> add.
        """
        call_order: list[str] = []

        repo = AsyncMock()
        repo.check_slug_exists = AsyncMock(
            side_effect=lambda *_: call_order.append("check") or False
        )

        original_create = None

        # Patch Product.create to record call order
        from src.modules.catalog.domain.entities import Product

        original_create = Product.create

        def recording_create(**kwargs: object) -> object:
            call_order.append("create")
            return original_create(**kwargs)  # type: ignore[arg-type]

        with patch.object(Product, "create", side_effect=recording_create):
            repo.add = AsyncMock(side_effect=lambda *_: call_order.append("add"))
            uow = make_uow()
            handler = CreateProductHandler(product_repo=repo, uow=uow)
            await handler.handle(make_command())

        assert call_order.index("check") < call_order.index("create")
        assert call_order.index("create") < call_order.index("add")

    @pytest.mark.parametrize(
        "country_code",
        ["US", "DE", "UZ", "GB", None],
    )
    async def test_country_of_origin_variants(self, country_code: str | None) -> None:
        """Various country_of_origin values (including None) are accepted."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={"en": "Product"},
            slug=f"product-{country_code or 'none'}",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            country_of_origin=country_code,
        )
        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.country_of_origin == country_code

    async def test_supplier_id_none_by_default(self) -> None:
        """When supplier_id is omitted the product's supplier_id is None."""
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        await handler.handle(make_command())

        product = repo.add.call_args[0][0]
        assert product.supplier_id is None

    async def test_supplier_id_set_when_provided(self) -> None:
        """When supplier_id is provided it is forwarded to the product."""
        supplier_id = uuid.uuid4()
        repo = make_product_repo(slug_exists=False)
        uow = make_uow()
        handler = CreateProductHandler(product_repo=repo, uow=uow)

        cmd = CreateProductCommand(
            title_i18n={"en": "Gadget"},
            slug="gadget",
            brand_id=uuid.uuid4(),
            primary_category_id=uuid.uuid4(),
            supplier_id=supplier_id,
        )
        await handler.handle(cmd)

        product = repo.add.call_args[0][0]
        assert product.supplier_id == supplier_id
