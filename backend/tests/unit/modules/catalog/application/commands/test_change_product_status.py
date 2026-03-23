"""Unit tests for ChangeProductStatusCommand and ChangeProductStatusHandler.

Covers:
  - Command dataclass fields and immutability
  - Handler happy path: product found, valid transition, updated, committed
  - Handler not found: raises ProductNotFoundError, no commit
  - Handler invalid transition: raises InvalidStatusTransitionError, no commit
  - UoW used as async context manager
  - repo.update called with the transitioned product
  - All valid FSM transitions succeed
  - All invalid FSM transitions are rejected
"""

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.catalog.application.commands.change_product_status import (
    ChangeProductStatusCommand,
    ChangeProductStatusHandler,
)
from src.modules.catalog.domain.exceptions import (
    InvalidStatusTransitionError,
    ProductNotFoundError,
)
from src.modules.catalog.domain.value_objects import ProductStatus

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


def make_media_repo(has_media: bool = True) -> AsyncMock:
    """Build a mocked IMediaAssetRepository.

    Args:
        has_media: Whether list_by_product returns at least one media asset.
    """
    repo = AsyncMock()
    if has_media:
        media = MagicMock()
        repo.list_by_product = AsyncMock(return_value=[media])
    else:
        repo.list_by_product = AsyncMock(return_value=[])
    return repo


def make_product_repo(product: MagicMock | None = None) -> AsyncMock:
    """Build a mocked IProductRepository.

    Args:
        product: The product to return from get(), or None for not-found.

    Returns:
        Configured AsyncMock.
    """
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=product)
    repo.update = AsyncMock()
    return repo


def make_product(
    product_id: uuid.UUID | None = None,
    status: ProductStatus = ProductStatus.DRAFT,
) -> MagicMock:
    """Build a minimal mock Product domain entity with a real transition_status.

    Uses a real Product entity under the hood so that FSM validation
    is exercised (not mocked away).
    """
    from src.modules.catalog.domain.entities import Product

    real_product: Product = Product.create(
        slug=f"test-product-{uuid.uuid4().hex[:6]}",
        title_i18n={"en": "Test Product"},
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
    )
    # Walk the product to the desired status via valid transitions.
    _walk_to_status(real_product, status)
    return real_product


def _walk_to_status(product: object, target: ProductStatus) -> None:
    """Transition a real Product entity to the target status via valid FSM paths."""
    from src.modules.catalog.domain.entities import Product

    assert isinstance(product, Product)

    # BFS path through the FSM.
    paths: dict[ProductStatus, list[ProductStatus]] = {
        ProductStatus.DRAFT: [],
        ProductStatus.ENRICHING: [ProductStatus.ENRICHING],
        ProductStatus.READY_FOR_REVIEW: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
        ],
        ProductStatus.PUBLISHED: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
        ],
        ProductStatus.ARCHIVED: [
            ProductStatus.ENRICHING,
            ProductStatus.READY_FOR_REVIEW,
            ProductStatus.PUBLISHED,
            ProductStatus.ARCHIVED,
        ],
    }
    for step in paths[target]:
        product.transition_status(step)


def make_command(
    product_id: uuid.UUID | None = None,
    new_status: ProductStatus = ProductStatus.ENRICHING,
) -> ChangeProductStatusCommand:
    """Build a ChangeProductStatusCommand with sensible defaults."""
    return ChangeProductStatusCommand(
        product_id=product_id or uuid.uuid4(),
        new_status=new_status,
    )


# ---------------------------------------------------------------------------
# ChangeProductStatusCommand
# ---------------------------------------------------------------------------


class TestChangeProductStatusCommand:
    """Structural tests for the ChangeProductStatusCommand DTO."""

    def test_fields_stored_correctly(self) -> None:
        """Both fields are stored on the dataclass."""
        pid = uuid.uuid4()
        cmd = ChangeProductStatusCommand(
            product_id=pid,
            new_status=ProductStatus.ENRICHING,
        )
        assert cmd.product_id == pid
        assert cmd.new_status == ProductStatus.ENRICHING

    def test_command_is_frozen(self) -> None:
        """ChangeProductStatusCommand is a frozen dataclass -- mutation must raise."""
        cmd = make_command()
        with pytest.raises(FrozenInstanceError):
            cmd.new_status = ProductStatus.DRAFT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ChangeProductStatusHandler -- happy path
# ---------------------------------------------------------------------------


class TestChangeProductStatusHandlerHappyPath:
    """Handler tests when the product exists and the transition is valid."""

    async def test_calls_repo_get_with_product_id(self) -> None:
        """Handler calls repo.get with the command's product_id."""
        pid = uuid.uuid4()
        product = make_product(product_id=pid, status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(make_command(product_id=pid, new_status=ProductStatus.ENRICHING))

        repo.get.assert_awaited_once_with(pid)

    async def test_product_status_is_updated(self) -> None:
        """After handling, the product's status equals the new_status."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        assert product.status == ProductStatus.ENRICHING

    async def test_calls_repo_update_with_product(self) -> None:
        """Handler calls repo.update with the transitioned product."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        repo.update.assert_awaited_once_with(product)

    async def test_calls_uow_commit_once(self) -> None:
        """Handler commits the UoW exactly once on success."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        uow.commit.assert_awaited_once()

    async def test_uow_used_as_context_manager(self) -> None:
        """Handler enters and exits the UoW async context manager."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        uow.__aenter__.assert_awaited_once()
        uow.__aexit__.assert_awaited_once()

    async def test_returns_none(self) -> None:
        """Handler returns None (command returns no result)."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        result = await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=ProductStatus.ENRICHING,
            )
        )

        assert result is None


# ---------------------------------------------------------------------------
# ChangeProductStatusHandler -- product not found
# ---------------------------------------------------------------------------


class TestChangeProductStatusHandlerNotFound:
    """Handler tests when the product does not exist."""

    async def test_raises_product_not_found_error(self) -> None:
        """Handler raises ProductNotFoundError when repo.get returns None."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

    async def test_error_contains_product_id(self) -> None:
        """Raised ProductNotFoundError message includes the product_id."""
        pid = uuid.uuid4()
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(ProductNotFoundError) as exc_info:
            await handler.handle(make_command(product_id=pid))

        assert str(pid) in str(exc_info.value)

    async def test_repo_update_not_called(self) -> None:
        """When product not found, repo.update must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        repo.update.assert_not_awaited()

    async def test_commit_not_called(self) -> None:
        """When product not found, uow.commit must not be called."""
        repo = make_product_repo(product=None)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(ProductNotFoundError):
            await handler.handle(make_command())

        uow.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# ChangeProductStatusHandler -- invalid transitions
# ---------------------------------------------------------------------------


class TestChangeProductStatusHandlerInvalidTransition:
    """Handler tests when the FSM transition is not allowed."""

    async def test_draft_to_published_raises_error(self) -> None:
        """DRAFT -> PUBLISHED is not a valid transition."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.PUBLISHED,
                )
            )

    async def test_draft_to_archived_raises_error(self) -> None:
        """DRAFT -> ARCHIVED is not a valid transition."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.ARCHIVED,
                )
            )

    async def test_published_to_draft_raises_error(self) -> None:
        """PUBLISHED -> DRAFT is not a valid transition."""
        product = make_product(status=ProductStatus.PUBLISHED)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.DRAFT,
                )
            )

    async def test_invalid_transition_does_not_commit(self) -> None:
        """When transition is invalid, uow.commit must not be called."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.PUBLISHED,
                )
            )

        uow.commit.assert_not_awaited()

    async def test_invalid_transition_does_not_update(self) -> None:
        """When transition is invalid, repo.update must not be called."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.PUBLISHED,
                )
            )

        repo.update.assert_not_awaited()

    async def test_same_status_raises_error(self) -> None:
        """Transitioning to the same status is not allowed (self-loop)."""
        product = make_product(status=ProductStatus.DRAFT)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=ProductStatus.DRAFT,
                )
            )


# ---------------------------------------------------------------------------
# ChangeProductStatusHandler -- all valid FSM transitions
# ---------------------------------------------------------------------------


class TestChangeProductStatusHandlerValidTransitions:
    """Parametrized tests for every valid FSM transition."""

    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            (ProductStatus.DRAFT, ProductStatus.ENRICHING),
            (ProductStatus.ENRICHING, ProductStatus.DRAFT),
            (ProductStatus.ENRICHING, ProductStatus.READY_FOR_REVIEW),
            (ProductStatus.READY_FOR_REVIEW, ProductStatus.ENRICHING),
            (ProductStatus.READY_FOR_REVIEW, ProductStatus.PUBLISHED),
            (ProductStatus.PUBLISHED, ProductStatus.ARCHIVED),
            (ProductStatus.ARCHIVED, ProductStatus.DRAFT),
        ],
        ids=[
            "draft-to-enriching",
            "enriching-to-draft",
            "enriching-to-ready_for_review",
            "ready_for_review-to-enriching",
            "ready_for_review-to-published",
            "published-to-archived",
            "archived-to-draft",
        ],
    )
    async def test_valid_transition_succeeds(
        self,
        from_status: ProductStatus,
        to_status: ProductStatus,
    ) -> None:
        """Each valid FSM transition updates the product status and commits."""
        product = make_product(status=from_status)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        await handler.handle(
            ChangeProductStatusCommand(
                product_id=product.id,
                new_status=to_status,
            )
        )

        assert product.status == to_status
        repo.update.assert_awaited_once_with(product)
        uow.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# ChangeProductStatusHandler -- all invalid FSM transitions
# ---------------------------------------------------------------------------


class TestChangeProductStatusHandlerInvalidTransitions:
    """Parametrized tests for a selection of invalid FSM transitions."""

    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            (ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW),
            (ProductStatus.DRAFT, ProductStatus.PUBLISHED),
            (ProductStatus.DRAFT, ProductStatus.ARCHIVED),
            (ProductStatus.ENRICHING, ProductStatus.PUBLISHED),
            (ProductStatus.ENRICHING, ProductStatus.ARCHIVED),
            (ProductStatus.READY_FOR_REVIEW, ProductStatus.DRAFT),
            (ProductStatus.READY_FOR_REVIEW, ProductStatus.ARCHIVED),
            (ProductStatus.PUBLISHED, ProductStatus.DRAFT),
            (ProductStatus.PUBLISHED, ProductStatus.ENRICHING),
            (ProductStatus.PUBLISHED, ProductStatus.READY_FOR_REVIEW),
            (ProductStatus.ARCHIVED, ProductStatus.ENRICHING),
            (ProductStatus.ARCHIVED, ProductStatus.READY_FOR_REVIEW),
            (ProductStatus.ARCHIVED, ProductStatus.PUBLISHED),
            (ProductStatus.ARCHIVED, ProductStatus.ARCHIVED),
        ],
        ids=[
            "draft-to-ready_for_review",
            "draft-to-published",
            "draft-to-archived",
            "enriching-to-published",
            "enriching-to-archived",
            "ready_for_review-to-draft",
            "ready_for_review-to-archived",
            "published-to-draft",
            "published-to-enriching",
            "published-to-ready_for_review",
            "archived-to-enriching",
            "archived-to-ready_for_review",
            "archived-to-published",
            "archived-to-archived",
        ],
    )
    async def test_invalid_transition_raises_error(
        self,
        from_status: ProductStatus,
        to_status: ProductStatus,
    ) -> None:
        """Each invalid FSM transition raises InvalidStatusTransitionError."""
        product = make_product(status=from_status)
        repo = make_product_repo(product=product)
        uow = make_uow()
        handler = ChangeProductStatusHandler(
            product_repo=repo, media_repo=make_media_repo(), uow=uow
        )

        with pytest.raises(InvalidStatusTransitionError):
            await handler.handle(
                ChangeProductStatusCommand(
                    product_id=product.id,
                    new_status=to_status,
                )
            )
