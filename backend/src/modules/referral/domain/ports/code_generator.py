"""Code-generator port — produces the 8-character public referral code."""

from __future__ import annotations

from typing import Protocol


class ICodeGenerator(Protocol):
    """Generate a fresh referral code string.

    Implementations choose the alphabet and length, must yield a
    different value on every call (with negligible collision rate),
    and must be safe to call concurrently.
    """

    def generate(self) -> str: ...
