"""Dishka IoC provider for the Recipient module.

Post-Sprint-1.5 Part 2: validator + dobropost-passport consumer
removed. Their counterparts live (or will live, when wired) in the
``passport`` bounded context.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.recipient.application.commands.archive_recipient import (
    ArchiveRecipientHandler,
)
from src.modules.recipient.application.commands.create_recipient import (
    CreateRecipientHandler,
)
from src.modules.recipient.application.commands.update_recipient import (
    UpdateRecipientHandler,
)
from src.modules.recipient.application.queries.get_recipient import (
    GetRecipientHandler,
)
from src.modules.recipient.application.queries.list_my_recipients import (
    ListMyRecipientsHandler,
)
from src.modules.recipient.domain.interfaces import IRecipientRepository
from src.modules.recipient.infrastructure.repositories.recipient_repository import (
    RecipientRepository,
)


class RecipientProvider(Provider):
    repo: CompositeDependencySource = provide(
        RecipientRepository, scope=Scope.REQUEST, provides=IRecipientRepository
    )

    create_handler: CompositeDependencySource = provide(
        CreateRecipientHandler, scope=Scope.REQUEST
    )
    update_handler: CompositeDependencySource = provide(
        UpdateRecipientHandler, scope=Scope.REQUEST
    )
    archive_handler: CompositeDependencySource = provide(
        ArchiveRecipientHandler, scope=Scope.REQUEST
    )

    get_handler: CompositeDependencySource = provide(
        GetRecipientHandler, scope=Scope.REQUEST
    )
    list_handler: CompositeDependencySource = provide(
        ListMyRecipientsHandler, scope=Scope.REQUEST
    )
