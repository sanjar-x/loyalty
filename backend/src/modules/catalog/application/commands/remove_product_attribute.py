"""
Backward-compatibility re-exports.

This module has been renamed to ``delete_product_attribute`` to follow the
project naming convention: "Delete" for persistence operations, "Delete"
for in-memory aggregate child operations.

All symbols are re-exported here so existing imports continue to work.
"""

from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeCommand as DeleteProductAttributeCommand,
)
from src.modules.catalog.application.commands.delete_product_attribute import (
    DeleteProductAttributeHandler as DeleteProductAttributeHandler,
)

__all__ = [
    "DeleteProductAttributeCommand",
    "DeleteProductAttributeHandler",
]
