"""Canonical SupplierType taxonomy — shared kernel (TYPE-002).

Promoted from ``modules/supplier/domain/value_objects.py`` because the
type is referenced across multiple bounded contexts:

* **catalog** — surfaced on product / SKU cards (cross-border vs local).
* **cart** — drives cart-level customs warnings and FX-rate selection.
* **order** — pickup carrier eligibility and customs declaration flow.
* **pricing** — supplier-type → pricing-context mapping (ADR-005).
* **logistics** — booking provider routing (DobroPost for cross-border).

Living in shared kernel removes the cross-module domain-import smell
that would otherwise spread the supplier-type axis as raw strings
across cart/order/pricing entities. Closed StrEnum so a typo
(``"cross-border"`` with a hyphen) raises at construction time
instead of silently skipping the cross-border flow.
"""

from __future__ import annotations

import enum


class SupplierType(enum.StrEnum):
    """Classification of supplier by geography and logistics model.

    * ``CROSS_BORDER`` — Chinese marketplace suppliers (Poizon,
      Taobao, Yupoo, …). Cross-border customs declaration applies.
    * ``LOCAL`` — Russian regional suppliers. Domestic logistics path.
    """

    CROSS_BORDER = "cross_border"
    LOCAL = "local"
