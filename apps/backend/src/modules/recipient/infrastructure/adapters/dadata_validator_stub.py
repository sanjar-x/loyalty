"""DaData passport validator — stub implementation.

Real DaData integration (`dadata.ru/api/find-fms-unit/`) is a future
SPEC. The stub fails for the deterministic test pattern
``passport_serial=='0000' and passport_number=='000000'`` so unit tests
can exercise the failure branch.
"""

from src.modules.recipient.domain.entities import Recipient
from src.modules.recipient.domain.interfaces import (
    IRecipientValidator,
    ValidationResult,
)


class DaDataValidatorStub(IRecipientValidator):
    async def validate(self, recipient: Recipient) -> ValidationResult:
        if (
            recipient.customs_data.passport_serial == "0000"
            and recipient.customs_data.passport_number == "000000"
        ):
            return ValidationResult(
                is_valid=False,
                reason="DaData stub: deterministic test failure pattern",
            )
        return ValidationResult(is_valid=True)
