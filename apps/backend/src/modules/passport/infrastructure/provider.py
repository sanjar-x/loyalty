"""Dishka provider for the Passport bounded context."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.passport.application.commands.archive_passport import (
    ArchivePassportHandler,
)
from src.modules.passport.application.commands.create_passport import (
    CreatePassportHandler,
)
from src.modules.passport.application.commands.update_passport import (
    UpdatePassportHandler,
)
from src.modules.passport.application.queries.get_passport import GetPassportHandler
from src.modules.passport.application.queries.list_my_passports import (
    ListMyPassportsHandler,
)
from src.modules.passport.domain.interfaces import IPassportRepository
from src.modules.passport.infrastructure.repositories.passport_repository import (
    PassportRepository,
)


class PassportProvider(Provider):
    passport_repo: CompositeDependencySource = provide(
        PassportRepository, scope=Scope.REQUEST, provides=IPassportRepository
    )

    create_passport_handler: CompositeDependencySource = provide(
        CreatePassportHandler, scope=Scope.REQUEST
    )
    update_passport_handler: CompositeDependencySource = provide(
        UpdatePassportHandler, scope=Scope.REQUEST
    )
    archive_passport_handler: CompositeDependencySource = provide(
        ArchivePassportHandler, scope=Scope.REQUEST
    )
    get_passport_handler: CompositeDependencySource = provide(
        GetPassportHandler, scope=Scope.REQUEST
    )
    list_my_passports_handler: CompositeDependencySource = provide(
        ListMyPassportsHandler, scope=Scope.REQUEST
    )
