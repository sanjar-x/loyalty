"""Favorites domain exceptions.

Each subclass picks a shared exception base from
``src/shared/exceptions.py`` to inherit the right HTTP status code
and the uniform error envelope.
"""

import uuid

from shared.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableEntityError,
)


class FavoriteListNotFoundError(NotFoundError):
    def __init__(self, *, list_id: uuid.UUID | None = None) -> None:
        super().__init__(
            message=(
                f"Favorite list not found: {list_id}"
                if list_id is not None
                else "Favorite list not found"
            ),
            error_code="FAVORITE_LIST_NOT_FOUND",
        )


class FavoriteListNameConflictError(ConflictError):
    def __init__(self, *, name: str) -> None:
        super().__init__(
            message=f"Favorite list with name {name!r} already exists",
            error_code="FAVORITE_LIST_NAME_CONFLICT",
            details={"name": name},
        )


class FavoriteListNotOwnedError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__(
            message="Favorite list does not belong to the authenticated user",
            error_code="FAVORITE_LIST_NOT_OWNED",
        )


class DefaultListImmutableError(UnprocessableEntityError):
    def __init__(self, *, action: str) -> None:
        super().__init__(
            message=f"Cannot {action} the default favorite list",
            error_code="FAVORITE_DEFAULT_LIST_IMMUTABLE",
            details={"action": action},
        )


class FavoriteTargetInvalidError(UnprocessableEntityError):
    def __init__(self, *, target_type: str, target_id: uuid.UUID, reason: str) -> None:
        super().__init__(
            message=(f"Favorite target invalid ({target_type}={target_id}): {reason}"),
            error_code="FAVORITE_TARGET_INVALID",
            details={
                "target_type": target_type,
                "target_id": str(target_id),
                "reason": reason,
            },
        )
