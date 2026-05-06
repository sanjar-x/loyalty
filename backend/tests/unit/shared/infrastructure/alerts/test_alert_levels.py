"""Contract tests for the alert formatter (HARD-2)."""

from __future__ import annotations

import pytest

from src.shared.infrastructure.alerts.alert_levels import AlertLevel, format_alert

pytestmark = pytest.mark.unit


class TestAlertLevelEnum:
    def test_values_are_strenum_payloads(self):
        # StrEnum: str(member) returns the enum value, not the repr.
        assert str(AlertLevel.INFO) == "INFO"
        assert str(AlertLevel.WARNING) == "WARNING"
        assert str(AlertLevel.CRITICAL) == "CRITICAL"

    def test_three_severities(self):
        # The kernel commits to exactly three levels; tests pin that
        # contract so a future addition is a deliberate decision.
        assert {member.value for member in AlertLevel} == {
            "INFO",
            "WARNING",
            "CRITICAL",
        }


class TestFormatAlert:
    def test_info_prefix(self):
        text = format_alert(AlertLevel.INFO, title="Hello", body="world")
        assert text.startswith("ℹ️ INFO — Hello")
        assert "\n\nworld" in text

    def test_warning_prefix(self):
        text = format_alert(AlertLevel.WARNING, title="Lag", body="42 pending")
        assert text.startswith("⚠️ WARNING — Lag")
        assert "42 pending" in text

    def test_critical_prefix(self):
        text = format_alert(AlertLevel.CRITICAL, title="Outage", body="db unreachable")
        assert text.startswith("🚨 CRITICAL — Outage")
        assert "db unreachable" in text

    def test_body_separated_by_blank_line(self):
        # The body is offset by a blank line so Telegram renders the
        # title prominently. Locking this so accidental concatenation
        # changes are caught.
        text = format_alert(AlertLevel.INFO, title="T", body="B")
        title_line, blank, body_line = text.split("\n", 2)
        assert blank == ""
        assert title_line.endswith("— T")
        assert body_line == "B"

    def test_title_kw_only(self):
        with pytest.raises(TypeError):
            # `title` and `body` are kw-only — positional misuse must fail
            # so call sites stay readable.
            format_alert(AlertLevel.INFO, "T", "B")  # ty: ignore[missing-argument,too-many-positional-arguments]
