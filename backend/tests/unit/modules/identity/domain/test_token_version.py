from src.modules.identity.domain.value_objects import PrimaryAuthMethod
from src.modules.identity.domain.entities import Identity


class TestTokenVersion:
    def test_default_token_version_is_one(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        assert identity.token_version == 1

    def test_bump_increments_version(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        old_updated = identity.updated_at
        identity.bump_token_version()
        assert identity.token_version == 2
        assert identity.updated_at >= old_updated

    def test_multiple_bumps(self):
        identity = Identity.register(PrimaryAuthMethod.LOCAL)
        identity.bump_token_version()
        identity.bump_token_version()
        identity.bump_token_version()
        assert identity.token_version == 4
