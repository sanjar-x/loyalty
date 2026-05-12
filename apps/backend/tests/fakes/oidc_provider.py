# tests/fakes/oidc_provider.py
"""
Stub implementation of IOIDCProvider for testing.
Returns configurable OIDCUserInfo without real OAuth calls.
"""

from src.shared.interfaces.security import OIDCUserInfo


class StubOIDCProvider:
    """Stub that returns pre-configured OIDC user info."""

    def __init__(
        self,
        default_user: OIDCUserInfo | None = None,
    ) -> None:
        self._default_user = default_user or OIDCUserInfo(
            provider="google",
            sub="stub-oidc-sub-12345",
            email="oidc-user@example.com",
        )
        self._users: dict[str, OIDCUserInfo] = {}

    def configure_token(self, token: str, user_info: OIDCUserInfo) -> None:
        """Pre-configure a token -> user mapping for testing."""
        self._users[token] = user_info

    async def validate_token(self, token: str) -> OIDCUserInfo:
        if token in self._users:
            return self._users[token]
        return self._default_user

    async def get_authorization_url(self, state: str) -> str:
        return f"https://fake-oidc.test/authorize?state={state}"
