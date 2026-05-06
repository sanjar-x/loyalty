"""Domain-side ports (Hexagonal) for the referral bounded context.

Implementations live in ``src.modules.referral.infrastructure``.
"""

from src.modules.referral.domain.ports.code_generator import ICodeGenerator
from src.modules.referral.domain.ports.customer_directory import (
    CustomerSnapshot,
    ICustomerDirectory,
)
from src.modules.referral.domain.ports.fraud_evaluator import (
    FraudContext,
    FraudVerdictKind,
    IFraudEvaluator,
)
from src.modules.referral.domain.ports.order_directory import (
    IOrderDirectory,
    OrderSnapshot,
)
from src.modules.referral.domain.ports.repositories import (
    ICustomerLoyaltyRepository,
    IReferralCodeRepository,
    IReferralRepository,
    IReferralRewardRepository,
)

__all__ = [
    "CustomerSnapshot",
    "FraudContext",
    "FraudVerdictKind",
    "ICodeGenerator",
    "ICustomerDirectory",
    "ICustomerLoyaltyRepository",
    "IFraudEvaluator",
    "IOrderDirectory",
    "IReferralCodeRepository",
    "IReferralRepository",
    "IReferralRewardRepository",
    "OrderSnapshot",
]
