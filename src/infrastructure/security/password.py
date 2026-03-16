# src/infrastructure/security/password.py
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from src.shared.interfaces.security import IPasswordHasher


class Argon2PasswordHasher(IPasswordHasher):
    """
    Primary: Argon2id (OWASP recommendation).
    Backward-compatible: verifies legacy Bcrypt hashes and flags for rehash.
    """

    def __init__(self) -> None:
        self._password_hash = PasswordHash(
            hashers=(
                Argon2Hasher(),
                BcryptHasher(),
            )
        )

    def hash(self, password: str) -> str:
        """Hash with Argon2id (primary hasher)."""
        return self._password_hash.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify against both Argon2id and Bcrypt hashes."""
        return self._password_hash.verify(plain_password, hashed_password)

    def needs_rehash(self, hashed_password: str) -> bool:
        """True if hash is Bcrypt (legacy) and should be rehashed to Argon2id."""
        return hashed_password.startswith(("$2a$", "$2b$", "$2y$"))
