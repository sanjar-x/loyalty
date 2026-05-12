"""Canonical ``Money`` domain value object — shared kernel (REC-032 D5).

Promoted from ``catalog/domain/value_objects.Money`` so any module that
needs an immutable currency-aware monetary amount uses the same type
instead of declaring its own. The wire-shape twin lives in
:class:`shared.schemas.MoneySchema` (CAT-018).

Logistics historically declared a parallel ``Money`` value object with a
different field name (``currency_code`` instead of ``currency``); that
divergence is left to a follow-up REC-035 mass-rename — promotion of
the canonical type here is the prerequisite.
"""

from __future__ import annotations

from attrs import frozen


# ``@frozen`` does not generate ordering methods by default in attrs, so
# the custom ``__lt__/__le__/__gt__/__ge__`` below are safe to define
# without conflict. ``__attrs_post_init__`` in a frozen class must only
# read fields, never assign — the ``object.__setattr__`` escape hatch
# is the documented exception used here to uppercase the currency code
# in-place after the attrs constructor runs.
@frozen
class Money:
    """Immutable value object representing a monetary amount.

    Stores the amount in the smallest currency units (e.g. kopecks for
    RUB, cents for USD) to avoid floating-point rounding errors.
    Currency is validated to be exactly 3 characters per ISO 4217;
    full whitelist validation is deferred to the presentation layer.

    Ordering comparisons are only meaningful within the same currency.
    Comparing instances with different currencies raises ``ValueError``
    to prevent silent currency confusion.

    Attributes:
        amount: Non-negative integer in smallest currency units (e.g.
            kopecks).
        currency: 3-character ISO 4217 currency code (e.g. "RUB", "USD").

    Raises:
        ValueError: If ``amount`` is negative at construction time.
        ValueError: If ``currency`` is not exactly 3 characters at
            construction time.
        ValueError: If ordering comparison is attempted between
            instances with different ``currency`` values.
    """

    amount: int
    currency: str

    def __attrs_post_init__(self) -> None:
        """Validate field values after attrs-generated __init__ runs."""
        if self.amount < 0:
            raise ValueError("Money amount must be non-negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character ISO code")
        object.__setattr__(self, "currency", self.currency.upper())

    @staticmethod
    def from_primitives(
        amount: int,
        currency: str,
        compare_at_amount: int | None = None,
    ) -> tuple[Money, Money | None]:
        """Build a price/compare-at-price pair from primitive values.

        Convenience factory that eliminates repeated Money construction
        boilerplate across command handlers.

        Args:
            amount: Price in smallest currency units.
            currency: 3-character ISO 4217 currency code.
            compare_at_amount: Optional compare-at (strikethrough) price.
                When provided, must be strictly greater than *amount*.

        Returns:
            Tuple of ``(price, compare_at_price)``. ``compare_at_price``
            is ``None`` when *compare_at_amount* is ``None``.

        Raises:
            ValueError: If *compare_at_amount* is not greater than *amount*.
        """
        price = Money(amount=amount, currency=currency)
        compare_at_price: Money | None = None
        if compare_at_amount is not None:
            if compare_at_amount <= amount:
                raise ValueError("compare_at_price must be greater than price")
            compare_at_price = Money(amount=compare_at_amount, currency=currency)
        return price, compare_at_price

    def _check_currency(self, other: Money) -> None:
        """Assert both instances share the same currency.

        Args:
            other: The Money instance being compared against.

        Raises:
            ValueError: If ``self.currency != other.currency``.
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare Money with different currencies: "
                f"{self.currency} vs {other.currency}"
            )

    def __lt__(self, other: object) -> bool:
        """Return True if this amount is strictly less than *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: object) -> bool:
        """Return True if this amount is less than or equal to *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: object) -> bool:
        """Return True if this amount is strictly greater than *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: object) -> bool:
        """Return True if this amount is greater than or equal to *other*."""
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount >= other.amount
