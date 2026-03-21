# tests/unit/shared/test_value_objects.py
"""Tests for Reference domain value objects."""

import pytest

from src.modules.geo.domain.value_objects import Country, Language

# ---------------------------------------------------------------------------
# Country — ISO 3166-1 value object
# ---------------------------------------------------------------------------


class TestCountryCreation:
    """Tests for valid Country construction."""

    def test_create_valid_country(self) -> None:
        country = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        assert country.alpha2 == "KZ"
        assert country.alpha3 == "KAZ"
        assert country.numeric == 398
        assert country.name == "Kazakhstan"

    def test_numeric_str_zero_padded(self) -> None:
        country = Country(alpha2="AL", alpha3="ALB", numeric=8, name="Albania")
        assert country.numeric_str == "008"

    def test_numeric_str_no_padding_needed(self) -> None:
        country = Country(alpha2="RU", alpha3="RUS", numeric=643, name="Russia")
        assert country.numeric_str == "643"

    def test_numeric_boundary_min(self) -> None:
        country = Country(alpha2="XX", alpha3="XXX", numeric=1, name="Test")
        assert country.numeric == 1
        assert country.numeric_str == "001"

    def test_numeric_boundary_max(self) -> None:
        country = Country(alpha2="XX", alpha3="XXX", numeric=999, name="Test")
        assert country.numeric == 999
        assert country.numeric_str == "999"


class TestCountryImmutability:
    """Country must be frozen (immutable)."""

    def test_cannot_set_alpha2(self) -> None:
        country = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        with pytest.raises(AttributeError):
            country.alpha2 = "RU"  # type: ignore[misc]

    def test_cannot_set_name(self) -> None:
        country = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        with pytest.raises(AttributeError):
            country.name = "Other"  # type: ignore[misc]


class TestCountryEquality:
    """Value equality semantics."""

    def test_equal_instances(self) -> None:
        a = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        b = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        assert a == b

    def test_different_alpha2(self) -> None:
        a = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        b = Country(alpha2="RU", alpha3="RUS", numeric=643, name="Russia")
        assert a != b

    def test_hashable(self) -> None:
        country = Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        assert hash(country) == hash(
            Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="Kazakhstan")
        )
        assert {country}  # usable in sets


class TestCountryAlpha2Validation:
    """Alpha-2 code validation."""

    def test_lowercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"alpha2.*2 uppercase"):
            Country(alpha2="kz", alpha3="KAZ", numeric=398, name="Kazakhstan")

    def test_single_char_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha2"):
            Country(alpha2="K", alpha3="KAZ", numeric=398, name="Kazakhstan")

    def test_three_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha2"):
            Country(alpha2="KAZ", alpha3="KAZ", numeric=398, name="Kazakhstan")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha2"):
            Country(alpha2="", alpha3="KAZ", numeric=398, name="Kazakhstan")

    def test_digits_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha2"):
            Country(alpha2="K1", alpha3="KAZ", numeric=398, name="Kazakhstan")


class TestCountryAlpha3Validation:
    """Alpha-3 code validation."""

    def test_lowercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"alpha3.*3 uppercase"):
            Country(alpha2="KZ", alpha3="kaz", numeric=398, name="Kazakhstan")

    def test_two_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha3"):
            Country(alpha2="KZ", alpha3="KA", numeric=398, name="Kazakhstan")

    def test_four_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha3"):
            Country(alpha2="KZ", alpha3="KAZZ", numeric=398, name="Kazakhstan")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="alpha3"):
            Country(alpha2="KZ", alpha3="", numeric=398, name="Kazakhstan")


class TestCountryNumericValidation:
    """Numeric code validation."""

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"numeric.*between"):
            Country(alpha2="KZ", alpha3="KAZ", numeric=0, name="Kazakhstan")

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"numeric.*between"):
            Country(alpha2="KZ", alpha3="KAZ", numeric=-1, name="Kazakhstan")

    def test_above_999_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"numeric.*between"):
            Country(alpha2="KZ", alpha3="KAZ", numeric=1000, name="Kazakhstan")


class TestCountryNameValidation:
    """Name validation."""

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"name.*non-empty"):
            Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="")

    def test_whitespace_only_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"name.*non-empty"):
            Country(alpha2="KZ", alpha3="KAZ", numeric=398, name="   ")


# ---------------------------------------------------------------------------
# Language — ISO 639 / BCP 47 value object
# ---------------------------------------------------------------------------

_UZ_KWARGS = dict(
    code="uz-Latn",
    iso639_1="uz",
    iso639_2="uzb",
    iso639_3="uzb",
    script="Latn",
    name_en="Uzbek (Latin)",
    name_native="Oʻzbekcha",
    direction="ltr",
)


def _lang(**overrides):
    return Language(**{**_UZ_KWARGS, **overrides})


class TestLanguageCreation:
    """Tests for valid Language construction."""

    def test_create_full(self) -> None:
        lang = _lang()
        assert lang.code == "uz-Latn"
        assert lang.iso639_1 == "uz"
        assert lang.iso639_2 == "uzb"
        assert lang.iso639_3 == "uzb"
        assert lang.script == "Latn"
        assert lang.name_en == "Uzbek (Latin)"
        assert lang.name_native == "Oʻzbekcha"
        assert lang.direction == "ltr"

    def test_create_minimal(self) -> None:
        lang = _lang(
            code="en",
            iso639_1=None,
            iso639_2=None,
            iso639_3=None,
            script=None,
        )
        assert lang.code == "en"
        assert lang.iso639_1 is None
        assert lang.script is None

    def test_rtl_direction(self) -> None:
        lang = _lang(code="ar", script="Arab", direction="rtl")
        assert lang.direction == "rtl"


class TestLanguageImmutability:
    def test_cannot_set_code(self) -> None:
        lang = _lang()
        with pytest.raises(AttributeError):
            lang.code = "ru"  # type: ignore[misc]


class TestLanguageEquality:
    def test_equal_instances(self) -> None:
        assert _lang() == _lang()

    def test_different_code(self) -> None:
        assert _lang(code="uz-Latn") != _lang(code="uz-Cyrl", script="Cyrl")

    def test_hashable(self) -> None:
        assert hash(_lang()) == hash(_lang())
        assert {_lang()}


class TestLanguageCodeValidation:
    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"code.*BCP 47"):
            _lang(code="")

    def test_single_char_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"code.*BCP 47"):
            _lang(code="u")

    def test_invalid_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"code.*BCP 47"):
            _lang(code="uz_Latn")  # underscore, not hyphen


class TestLanguageIso639_1Validation:
    def test_uppercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"iso639_1.*2 lowercase"):
            _lang(iso639_1="UZ")

    def test_three_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="iso639_1"):
            _lang(iso639_1="uzb")

    def test_none_allowed(self) -> None:
        lang = _lang(iso639_1=None)
        assert lang.iso639_1 is None


class TestLanguageIso639_2Validation:
    def test_uppercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"iso639_2.*3 lowercase"):
            _lang(iso639_2="UZB")

    def test_two_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="iso639_2"):
            _lang(iso639_2="uz")

    def test_none_allowed(self) -> None:
        lang = _lang(iso639_2=None)
        assert lang.iso639_2 is None


class TestLanguageIso639_3Validation:
    def test_uppercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"iso639_3.*3 lowercase"):
            _lang(iso639_3="UZB")

    def test_none_allowed(self) -> None:
        lang = _lang(iso639_3=None)
        assert lang.iso639_3 is None


class TestLanguageScriptValidation:
    def test_lowercase_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"script.*ISO 15924"):
            _lang(script="latn")

    def test_wrong_length_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"script.*ISO 15924"):
            _lang(script="La")

    def test_none_allowed(self) -> None:
        lang = _lang(script=None)
        assert lang.script is None


class TestLanguageNameValidation:
    def test_empty_name_en_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"name_en.*non-empty"):
            _lang(name_en="")

    def test_whitespace_name_en_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"name_en.*non-empty"):
            _lang(name_en="   ")

    def test_empty_name_native_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"name_native.*non-empty"):
            _lang(name_native="")


class TestLanguageDirectionValidation:
    def test_invalid_direction_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"direction.*ltr.*rtl"):
            _lang(direction="up")

    def test_empty_direction_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"direction.*ltr.*rtl"):
            _lang(direction="")
