"""Supplier domain value objects.

``SupplierType`` was promoted to the shared kernel in TYPE-002 because
it crosses bounded-context boundaries (cart/order/pricing/logistics
all branch on it). Re-exported here so existing imports
``from src.modules.supplier.domain.value_objects import SupplierType``
keep working.
"""

from shared.domain.supplier_type import SupplierType as SupplierType
