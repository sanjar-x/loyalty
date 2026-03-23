"""
Backward-compatibility re-exports.

This module has been renamed to ``delete_product_attribute`` to follow the
project naming convention: "Delete" for persistence operations, "Remove"
for in-memory aggregate child operations.

All symbols are re-exported here so existing imports continue to work.
"""

from src.modules.catalog.application.commands.delete_product_attribute import (  # noqa: F401
    DeleteProductAttributeCommand as RemoveProductAttributeCommand,
    DeleteProductAttributeHandler as RemoveProductAttributeHandler,
)

__all__ = [
    "RemoveProductAttributeCommand",
    "RemoveProductAttributeHandler",
]
