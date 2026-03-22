"""Geo domain exceptions.

Each exception maps to a specific business-rule violation within the
Geo bounded context. The presentation layer translates these into
HTTP error responses via the global exception handler.
"""

from src.shared.exceptions import NotFoundError


class CountryNotFoundError(NotFoundError):
    """Raised when a country lookup yields no result."""

    def __init__(self, country_code: str):
        super().__init__(
            message=f"Country with code '{country_code}' not found.",
            error_code="COUNTRY_NOT_FOUND",
            details={"country_code": country_code},
        )


class CurrencyNotFoundError(NotFoundError):
    """Raised when a currency lookup yields no result."""

    def __init__(self, currency_code: str):
        super().__init__(
            message=f"Currency with code '{currency_code}' not found.",
            error_code="CURRENCY_NOT_FOUND",
            details={"currency_code": currency_code},
        )


class LanguageNotFoundError(NotFoundError):
    """Raised when a language lookup yields no result."""

    def __init__(self, lang_code: str):
        super().__init__(
            message=f"Language with code '{lang_code}' not found.",
            error_code="LANGUAGE_NOT_FOUND",
            details={"lang_code": lang_code},
        )


class SubdivisionNotFoundError(NotFoundError):
    """Raised when a subdivision lookup yields no result."""

    def __init__(self, subdivision_code: str):
        super().__init__(
            message=f"Subdivision with code '{subdivision_code}' not found.",
            error_code="SUBDIVISION_NOT_FOUND",
            details={"subdivision_code": subdivision_code},
        )
