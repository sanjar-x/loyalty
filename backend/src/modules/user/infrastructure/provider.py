"""Dishka dependency injection provider for the User module.

Registers all User module repositories, command handlers, and query handlers
in the DI container at REQUEST scope.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.user.application.commands.anonymize_customer import (
    AnonymizeCustomerHandler,
)
from src.modules.user.application.commands.anonymize_user import AnonymizeUserHandler
from src.modules.user.application.commands.create_customer import CreateCustomerHandler
from src.modules.user.application.commands.create_staff_member import (
    CreateStaffMemberHandler,
)
from src.modules.user.application.commands.create_user import CreateUserHandler
from src.modules.user.application.commands.update_profile import UpdateProfileHandler
from src.modules.user.application.queries.get_my_profile import GetMyProfileHandler
from src.modules.user.application.queries.get_user_by_identity import (
    GetUserByIdentityHandler,
)
from src.modules.user.domain.interfaces import (
    ICustomerRepository,
    IStaffMemberRepository,
)
from src.modules.user.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from src.modules.user.infrastructure.repositories.staff_member_repository import (
    StaffMemberRepository,
)


class UserProvider(Provider):
    """Dishka provider that wires all User module dependencies.

    All dependencies are registered at REQUEST scope, meaning a new
    instance is created for each incoming request or task execution.
    """

    # Repositories
    customer_repo: CompositeDependencySource = provide(
        CustomerRepository, scope=Scope.REQUEST, provides=ICustomerRepository
    )
    staff_member_repo: CompositeDependencySource = provide(
        StaffMemberRepository, scope=Scope.REQUEST, provides=IStaffMemberRepository
    )

    # Command handlers (legacy)
    create_user_handler: CompositeDependencySource = provide(CreateUserHandler, scope=Scope.REQUEST)
    update_profile_handler: CompositeDependencySource = provide(
        UpdateProfileHandler, scope=Scope.REQUEST
    )
    anonymize_user_handler: CompositeDependencySource = provide(
        AnonymizeUserHandler, scope=Scope.REQUEST
    )

    # Command handlers (new)
    create_customer_handler: CompositeDependencySource = provide(
        CreateCustomerHandler, scope=Scope.REQUEST
    )
    create_staff_member_handler: CompositeDependencySource = provide(
        CreateStaffMemberHandler, scope=Scope.REQUEST
    )
    anonymize_customer_handler: CompositeDependencySource = provide(
        AnonymizeCustomerHandler, scope=Scope.REQUEST
    )

    # Query handlers
    get_my_profile_handler: CompositeDependencySource = provide(
        GetMyProfileHandler, scope=Scope.REQUEST
    )
    get_user_by_identity_handler: CompositeDependencySource = provide(
        GetUserByIdentityHandler, scope=Scope.REQUEST
    )
