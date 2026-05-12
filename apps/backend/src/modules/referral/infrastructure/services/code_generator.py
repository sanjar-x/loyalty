"""Concrete code generator implementing :class:`ICodeGenerator`.

Uses ``nanoid`` with the unambiguous alphabet declared on
:class:`ReferralProgrammePolicy`. Collision handling lives in the
``IssueReferralCode`` handler — on a UNIQUE-violation the handler
loops with a fresh code (the alphabet has 30 chars and the default
length is 8 → 30⁸ ≈ 6.5 × 10¹¹ combinations, so collisions are
astronomically rare even at scale).
"""

from __future__ import annotations

from nanoid import generate as nanoid_generate

from src.modules.referral.domain.policies import ReferralProgrammePolicy
from src.modules.referral.domain.ports import ICodeGenerator


class NanoidCodeGenerator(ICodeGenerator):
    def __init__(self, programme: ReferralProgrammePolicy) -> None:
        self._programme = programme

    def generate(self) -> str:
        return nanoid_generate(
            self._programme.code_alphabet, self._programme.code_length
        )
