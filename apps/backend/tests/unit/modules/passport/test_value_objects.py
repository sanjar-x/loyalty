"""Unit tests for Passport value objects (customs validators).

Ported 1:1 from the previous ``tests/unit/modules/recipient/
test_value_objects.py`` (ADR-011) so the migration backfill keeps
satisfying the same invariants.
"""

from datetime import date, timedelta
from typing import Any

import pytest

from src.modules.passport.domain.exceptions import (
    InvalidCustomsDataError,
    InvalidPassportFieldError,
)
from src.modules.passport.domain.value_objects import (
    CustomsData,
    FullName,
    PassportValidationStatus,
)

pytestmark = pytest.mark.unit


class TestFullName:
    def test_ru_and_lat_ok(self) -> None:
        n = FullName.parse(ru="Иван Иванов", lat="Ivan Ivanov")
        assert n.ru == "Иван Иванов"
        assert n.lat == "Ivan Ivanov"

    def test_ru_with_latin_rejected(self) -> None:
        with pytest.raises(InvalidPassportFieldError):
            FullName.parse(ru="Ivan Ivanov", lat="Ivan Ivanov")

    def test_lat_with_cyrillic_rejected(self) -> None:
        with pytest.raises(InvalidPassportFieldError):
            FullName.parse(ru="Иван", lat="Иван Ivanov")

    def test_empty_rejected(self) -> None:
        with pytest.raises(InvalidPassportFieldError):
            FullName.parse(ru="", lat="Ivan")
        with pytest.raises(InvalidPassportFieldError):
            FullName.parse(ru="Иван", lat="")


class TestCustomsData:
    def _ok_args(self) -> dict[str, Any]:
        return dict(
            passport_serial="1234",
            passport_number="567890",
            passport_issue_date=date(2015, 5, 22),
            birth_date=date(1990, 1, 1),
            inn="500100732272",
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


class TestPassportValidationStatusEnum:
    def test_values(self) -> None:
        assert PassportValidationStatus.PENDING.value == "pending"
        assert PassportValidationStatus.VERIFIED.value == "verified"
        assert PassportValidationStatus.INVALID.value == "invalid"
