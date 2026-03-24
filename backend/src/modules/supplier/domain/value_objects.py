"""Supplier domain value objects."""

import enum


class SupplierType(enum.StrEnum):
    """Classification of supplier by geography and logistics model.

    CROSS_BORDER: Chinese marketplace suppliers (Poizon, Taobao, etc.)
    LOCAL: Russian regional suppliers
    """

    CROSS_BORDER = "cross_border"
    LOCAL = "local"
