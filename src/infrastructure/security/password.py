from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from src.shared.interfaces.security import IPasswordHasher


class BcryptPasswordHasher(IPasswordHasher):
    """
    Автоматически обрабатывает параметры безопасности и генерацию соли (Salt).
    Использует Bcrypt под капотом.
    """

    def __init__(self):
        self._password_hash = PasswordHash((BcryptHasher(),))

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self._password_hash.verify(plain_password, hashed_password)
