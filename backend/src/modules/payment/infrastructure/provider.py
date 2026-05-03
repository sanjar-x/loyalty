"""Dishka IoC provider for the Payment bounded context."""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.payment.application.commands.capture_payment_intent import (
    CapturePaymentIntentHandler,
)
from src.modules.payment.application.commands.create_payment_intent import (
    CreatePaymentIntentHandler,
)
from src.modules.payment.application.commands.fail_payment_intent import (
    FailPaymentIntentHandler,
)
from src.modules.payment.application.commands.refund_payment_intent import (
    RefundPaymentIntentHandler,
)
from src.modules.payment.application.queries.get_payment_intent import (
    GetPaymentIntentHandler,
)
from src.modules.payment.domain.interfaces import (
    IPaymentIntentRepository,
    IPaymentProvider,
)
from src.modules.payment.infrastructure.providers.fake.provider import (
    FakePaymentProvider,
)
from src.modules.payment.infrastructure.repositories.payment_intent_repository import (
    PaymentIntentRepository,
)


class PaymentProviderDI(Provider):
    """DI provider for payment repositories, providers, and handlers."""

    intent_repo: CompositeDependencySource = provide(
        PaymentIntentRepository,
        scope=Scope.REQUEST,
        provides=IPaymentIntentRepository,
    )
    payment_provider: CompositeDependencySource = provide(
        FakePaymentProvider, scope=Scope.APP, provides=IPaymentProvider
    )

    create_intent_handler: CompositeDependencySource = provide(
        CreatePaymentIntentHandler, scope=Scope.REQUEST
    )
    capture_intent_handler: CompositeDependencySource = provide(
        CapturePaymentIntentHandler, scope=Scope.REQUEST
    )
    refund_intent_handler: CompositeDependencySource = provide(
        RefundPaymentIntentHandler, scope=Scope.REQUEST
    )
    fail_intent_handler: CompositeDependencySource = provide(
        FailPaymentIntentHandler, scope=Scope.REQUEST
    )

    get_intent_handler: CompositeDependencySource = provide(
        GetPaymentIntentHandler, scope=Scope.REQUEST
    )
