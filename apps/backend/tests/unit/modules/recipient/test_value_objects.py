"""Unit tests for Recipient value objects (validators)."""

from datetime import date, timedelta
from typing import Any

import pytest

from src.modules.recipient.domain.exceptions import (
    InvalidCustomsDataError,
    InvalidRecipientFieldError,
)
from src.modules.recipient.domain.value_objects import (
    CustomsData,
    Email,
    FullName,
    Phone,
    RecipientValidationStatus,
)

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


class TestCustomsData:
    def _ok_args(self) -> dict[str, Any]:
        return dict(
            passport_serial="1234",
            passport_number="567890",
            passport_issue_date=date(2015, 5, 22),
            birth_date=date(1990, 1, 1),
            inn="500100732272",  # valid checksum
        )

    def test_happy(self) -> None:
        c = CustomsData.parse(**self._ok_args())
        assert c.passport_serial == "1234"
        assert c.inn == "500100732272"

    def _with(self, **overrides: Any) -> dict[str, Any]:
        args = self._ok_args()
        args.update(overrides)
        return args

    def test_passport_serial_wrong_length(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(passport_serial="12345"))

    def test_passport_number_wrong_length(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(passport_number="12345"))

    def test_inn_wrong_checksum(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(inn="500100732250"))

    def test_inn_wrong_length(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(inn="12345"))

    def test_passport_issued_in_future_rejected(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(
                **self._with(passport_issue_date=date.today() + timedelta(days=1))
            )

    def test_passport_issued_before_1991_rejected(self) -> None:
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(passport_issue_date=date(1985, 1, 1)))

    def test_under_16_rejected(self) -> None:
        too_young = date.today() - timedelta(days=15 * 365)
        with pytest.raises(InvalidCustomsDataError):
            CustomsData.parse(**self._with(birth_date=too_young))


class TestRecipientValidationStatusEnum:
    def test_values(self) -> None:
        assert RecipientValidationStatus.PENDING.value == "pending"
        assert RecipientValidationStatus.VERIFIED.value == "verified"
        assert RecipientValidationStatus.INVALID.value == "invalid"
