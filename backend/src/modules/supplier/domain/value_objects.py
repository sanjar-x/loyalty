"""Supplier domain value objects."""

import enum


class SupplierType(str, enum.Enum):
    """Classification of supplier by geography and logistics model.

    CROSS_BORDER: Chinese marketplace suppliers (Poizon, Taobao, etc.)
    LOCAL: Russian regional suppliers
    """

    CROSS_BORDER = "cross_border"
    LOCAL = "local"
