"""Shared helpers for partial-update (PATCH) endpoints."""

from dataclasses import fields as dc_fields
from typing import Any


def build_update_command(
    request: Any,
    command_cls: type,
    *,
    exclude_from_provided: frozenset[str] = frozenset(),
    **fixed_kwargs: Any,
) -> Any:
    """Build a frozen-dataclass update command from a Pydantic PATCH request.

    Reads ``request.model_fields_set`` to determine which fields the client
    actually sent, maps them into command kwargs, and injects
    ``_provided_fields`` automatically.

    Args:
        request: Pydantic request model instance.
        command_cls: The frozen dataclass command class to instantiate.
        exclude_from_provided: Field names to exclude from _provided_fields
            (e.g. ``{"version"}``).
        **fixed_kwargs: Additional fixed keyword arguments (e.g.
            ``product_id=product_id``, ``sku_id=sku_id``).
    """
    provided = request.model_fields_set - exclude_from_provided
    cmd_kwargs: dict[str, Any] = {
        **fixed_kwargs,
        "_provided_fields": frozenset(provided),
    }
    for field_name in provided:
        value = getattr(request, field_name)
        cmd_kwargs[field_name] = value
    return command_cls(**cmd_kwargs)
