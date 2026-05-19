"""Unit tests for Recipient value objects (validators).

Post-ADR-011: customs PII validators (passport / INN / birth_date)
moved to ``tests/unit/modules/passport/test_value_objects.py``. This
file covers the shipping-only VOs that remain on Recipient.
"""

import pytest

from src.modules.recipient.domain.exceptions import InvalidRecipientFieldError
from src.modules.recipient.domain.value_objects import Email, FullName, Phone

pytestmark = pytest.mark.unit


class TestFullName:
    def test_ru_and_lat_ok(self) -> None:
        n = FullName.parse(ru="Иван Иванов", lat="Ivan Ivanov")
        assert n.ru == "Иван Иванов"
        assert n.lat == "Ivan Ivanov"

    def test_ru_with_latin_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            FullName.parse(ru="Ivan Ivanov", lat="Ivan Ivanov")

    def test_lat_with_cyrillic_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            FullName.parse(ru="Иван", lat="Иван Ivanov")

    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            FullName.parse(ru="", lat="Ivan")
        with pytest.raises(InvalidRecipientFieldError):
            FullName.parse(ru="Иван", lat="")


class TestPhone:
    def test_e164_ok(self) -> None:
        assert Phone.parse("+79108897762").e164 == "+79108897762"

    def test_strip_spaces_and_hyphens(self) -> None:
        assert Phone.parse("+7 910 889-77-62").e164 == "+79108897762"

    def test_non_ru_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            Phone.parse("+19108897762")

    def test_short_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            Phone.parse("+7910")


class TestEmail:
    def test_basic_ok(self) -> None:
        assert Email.parse("user@example.com").value == "user@example.com"

    def test_invalid_rejected(self) -> None:
        with pytest.raises(InvalidRecipientFieldError):
            Email.parse("notanemail")
        with pytest.raises(InvalidRecipientFieldError):
            Email.parse("a@b")  # missing dot in domain
