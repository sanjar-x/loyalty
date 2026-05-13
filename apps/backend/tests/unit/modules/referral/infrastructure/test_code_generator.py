"""Unit tests for :class:`NanoidCodeGenerator`."""

from __future__ import annotations

import pytest

from src.modules.referral.domain.policies import ReferralProgrammePolicy
from src.modules.referral.infrastructure.services.code_generator import (
    NanoidCodeGenerator,
)

pytestmark = pytest.mark.unit


class TestNanoidCodeGenerator:
    def test_default_length_and_alphabet(self) -> None:
        programme = ReferralProgrammePolicy()
        generator = NanoidCodeGenerator(programme=programme)

        for _ in range(100):
            code = generator.generate()
            assert len(code) == programme.code_length
            assert all(ch in programme.code_alphabet for ch in code)

    def test_codes_are_distinct_with_high_probability(self) -> None:
        # 30^8 ≈ 6.5×10^11 → 1 000 generations should have no collision.
        programme = ReferralProgrammePolicy()
        generator = NanoidCodeGenerator(programme=programme)
        produced = {generator.generate() for _ in range(1000)}
        assert len(produced) == 1000
