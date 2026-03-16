# src/modules/user/infrastructure/provider.py
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.user.application.commands.anonymize_user import AnonymizeUserHandler
from src.modules.user.application.commands.create_user import CreateUserHandler
from src.modules.user.application.commands.update_profile import UpdateProfileHandler
from src.modules.user.application.queries.get_my_profile import GetMyProfileHandler
from src.modules.user.application.queries.get_user_by_identity import (
    GetUserByIdentityHandler,
)
from src.modules.user.domain.interfaces import IUserRepository
from src.modules.user.infrastructure.repositories.user_repository import (
    UserRepository,
)


class UserProvider(Provider):
    # --- Repository (REQUEST scope) ---
    user_repo: CompositeDependencySource = provide(
        UserRepository, scope=Scope.REQUEST, provides=IUserRepository
    )

    # --- Command Handlers (REQUEST scope) ---
    create_user_handler: CompositeDependencySource = provide(
        CreateUserHandler, scope=Scope.REQUEST
    )
    update_profile_handler: CompositeDependencySource = provide(
        UpdateProfileHandler, scope=Scope.REQUEST
    )
    anonymize_user_handler: CompositeDependencySource = provide(
        AnonymizeUserHandler, scope=Scope.REQUEST
    )

    # --- Query Handlers (REQUEST scope) ---
    get_my_profile_handler: CompositeDependencySource = provide(
        GetMyProfileHandler, scope=Scope.REQUEST
    )
    get_user_by_identity_handler: CompositeDependencySource = provide(
        GetUserByIdentityHandler, scope=Scope.REQUEST
    )
