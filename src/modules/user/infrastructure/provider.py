"""Dishka dependency injection provider for the User module.

Registers all User module repositories, command handlers, and query handlers
in the DI container at REQUEST scope.
"""

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
    """Dishka provider that wires all User module dependencies.

    All dependencies are registered at REQUEST scope, meaning a new
    instance is created for each incoming request or task execution.
    """

    # Repository
    user_repo: CompositeDependencySource = provide(
        UserRepository, scope=Scope.REQUEST, provides=IUserRepository
    )

    # Command handlers
    create_user_handler: CompositeDependencySource = provide(CreateUserHandler, scope=Scope.REQUEST)
    update_profile_handler: CompositeDependencySource = provide(
        UpdateProfileHandler, scope=Scope.REQUEST
    )
    anonymize_user_handler: CompositeDependencySource = provide(
        AnonymizeUserHandler, scope=Scope.REQUEST
    )

    # Query handlers
    get_my_profile_handler: CompositeDependencySource = provide(
        GetMyProfileHandler, scope=Scope.REQUEST
    )
    get_user_by_identity_handler: CompositeDependencySource = provide(
        GetUserByIdentityHandler, scope=Scope.REQUEST
    )
