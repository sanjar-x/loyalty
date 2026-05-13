"""Unit tests for the order-side DobroPost status_id mapping."""

import pytest

from src.modules.order.infrastructure.dobropost_status_map import (
    DobroPostFsmAction,
    map_status_id_to_action,
    name_to_status_id,
    status_label,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("status_id", "action"),
    [
        # Arrival triggers
        (648, DobroPostFsmAction.ARRIVED_IN_RU),
        (649, DobroPostFsmAction.ARRIVED_IN_RU),
        # Passport invalid
        (544, DobroPostFsmAction.PASSPORT_INVALID),
        (545, DobroPostFsmAction.PASSPORT_INVALID),
        (590401, DobroPostFsmAction.PASSPORT_INVALID),
        # Customs reject
        (541, DobroPostFsmAction.CUSTOMS_REJECT),
        (542, DobroPostFsmAction.CUSTOMS_REJECT),
        (590413, DobroPostFsmAction.CUSTOMS_REJECT),
        # Lost
        (600, DobroPostFsmAction.PARCEL_LOST),
        # Informational
        (1, DobroPostFsmAction.NOOP),
        (500, DobroPostFsmAction.NOOP),
        (520, DobroPostFsmAction.NOOP),
        (570, DobroPostFsmAction.NOOP),
    ],
)
def test_map_status_id_to_action(status_id: int, action: DobroPostFsmAction) -> None:
    assert map_status_id_to_action(status_id) is action


def test_unknown_status_id_is_noop() -> None:
    assert map_status_id_to_action(123456) is DobroPostFsmAction.NOOP


def test_status_label_known_and_unknown() -> None:
    assert "Прибыл" not in status_label(648)  # exact label is fine — sanity check
    assert status_label(648).startswith("Подготовлено")
    assert "Неизвестный" in status_label(999_999)


def test_name_to_status_id_resolves_textual_status() -> None:
    assert name_to_status_id("Покинула таможню — передана на доставку по РФ") == 649
    assert name_to_status_id("Передан партнеру") == 9  # Cyrillic ё/е tolerant
    assert name_to_status_id("Whatever") is None
    assert name_to_status_id("") is None
