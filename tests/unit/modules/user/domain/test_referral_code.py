from src.modules.user.domain.services import generate_referral_code


class TestReferralCodeGeneration:
    def test_default_length_is_8(self):
        code = generate_referral_code()
        assert len(code) == 8

    def test_custom_length(self):
        code = generate_referral_code(length=12)
        assert len(code) == 12

    def test_excludes_ambiguous_chars(self):
        for _ in range(100):
            code = generate_referral_code()
            assert "O" not in code
            assert "0" not in code
            assert "I" not in code
            assert "1" not in code
            assert "L" not in code

    def test_unique_codes(self):
        codes = {generate_referral_code() for _ in range(1000)}
        assert len(codes) == 1000
