"""Password hashing implementation using Argon2id with Bcrypt fallback.

Primary hasher is Argon2id (OWASP recommendation). Legacy Bcrypt hashes
are verified for backward compatibility and flagged for rehashing.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.shared.interfaces.security import IPasswordHasher


class Argon2PasswordHasher(IPasswordHasher):
    """Password hasher using Argon2id as primary and Bcrypt as legacy fallback.

    New passwords are always hashed with Argon2id. Verification supports
    both Argon2id and Bcrypt hashes, and ``needs_rehash`` flags legacy
    Bcrypt hashes for transparent migration.
    """

    def __init__(self) -> None:
        """Initialize the hasher with Argon2id (primary) and Bcrypt (legacy)."""
        self._password_hash = PasswordHash(
            hashers=(
                Argon2Hasher(),
                BcryptHasher(),
            )
        )

    def hash(self, password: str) -> str:
        """Hash a password using Argon2id.

        Args:
            password: The plaintext password to hash.

        Returns:
            The Argon2id password hash string.
        """
        return self._password_hash.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against an Argon2id or Bcrypt hash.

        Args:
            plain_password: The plaintext password to verify.
            hashed_password: The stored hash to verify against.

        Returns:
            True if the password matches, False otherwise.
        """
        return self._password_hash.verify(plain_password, hashed_password)

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check whether a hash should be upgraded to the current Argon2id config.

        Detects both legacy Bcrypt hashes and Argon2id hashes produced with
        weaker parameters than the current configuration.

        Args:
            hashed_password: The stored hash to inspect.

        Returns:
            True if the hash should be rehashed (legacy algorithm or weak params).
        """
        for hasher in self._password_hash.hashers:
            if hasher.identify(hashed_password):
                return (
                    hasher != self._password_hash.hashers[0]
                    or hasher.check_needs_rehash(hashed_password)
                )
        return True
