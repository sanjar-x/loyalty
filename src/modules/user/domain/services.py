"""User domain services.

Contains stateless domain logic that doesn't belong to any single aggregate.
"""

import secrets

_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 30 chars, no O/0/I/1/L


def generate_referral_code(length: int = 8) -> str:
    """Generate a unique referral code.

    Uses cryptographically secure random selection from an unambiguous
    alphabet (30 chars). 30^8 ~ 6.5x10^11 combinations.

    Args:
        length: Code length (default 8).

    Returns:
        Random referral code string.
    """
    return "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(length))
