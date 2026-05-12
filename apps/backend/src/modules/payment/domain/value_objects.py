"""
Payment domain value objects.

Immutable types representing payment-domain concepts. Zero infrastructure
imports.
"""

import enum

from attrs import frozen


class PaymentIntentStatus(enum.StrEnum):
    """Lifecycle states for a PaymentIntent.

    FSM transitions::

        INITIATED  -> AUTHORIZED   (provider returned authorization)
        INITIATED  -> FAILED       (provider rejected)
        AUTHORIZED -> CAPTURED     (funds moved)
        AUTHORIZED -> CANCELLED    (authorization voided before capture)
        AUTHORIZED -> FAILED       (capture rejected)
        CAPTURED   -> REFUNDED     (refund issued)
        FAILED, CANCELLED, REFUNDED, CAPTURED (terminal for refund flow only) — terminal
    """

    INITIATED = "initiated"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProviderCode(enum.StrEnum):
    """Supported payment providers.

    ``fake`` is a deterministic in-process provider used outside ``prod``
    so that the full checkout flow can be exercised without external
    PSP integration. Real providers (YooKassa, СБП, Tinkoff) are added
    as separate adapters behind ``IPaymentProvider``.
    """

    FAKE = "fake"
    YOOKASSA = "yookassa"
    SBP = "sbp"
    TINKOFF = "tinkoff"


@frozen
class IdempotencyKey:
    """Provider-side idempotency key.

    Backend forwards client-supplied keys to the provider and stores
    them in ``payment_idempotency_keys`` with UNIQUE constraint so that
    a retried checkout does not double-charge.
    """

    value: str
