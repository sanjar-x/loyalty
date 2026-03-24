"""Dishka dependency injection provider for the User module.

Registers all repositories, command handlers, and query handlers
in the DI container at REQUEST scope.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.user.application.commands.anonymize_customer import (
    AnonymizeCustomerHandler,
)
from src.modules.user.application.commands.create_customer import CreateCustomerHandler
from src.modules.user.application.commands.create_staff_member import (
    CreateStaffMemberHandler,
)
from src.modules.user.application.commands.update_profile import UpdateProfileHandler
from src.modules.user.application.queries.get_customer_by_identity import (
    GetCustomerByIdentityHandler,
)
from src.modules.user.application.queries.get_my_profile import GetMyProfileHandler
from src.modules.user.domain.interfaces import (
    ICustomerRepository,
    IStaffMemberRepository,
    IUsernameUniquenessChecker,
)
from src.modules.user.infrastructure.repositories.customer_repository import (
    CustomerRepository,
)
from src.modules.user.infrastructure.repositories.staff_member_repository import (
    StaffMemberRepository,
)
from src.modules.user.infrastructure.services.username_checker import (
    UsernameUniquenessChecker,
)


class ProfileProvider(Provider):
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
    username_checker: CompositeDependencySource = provide(
        UsernameUniquenessChecker,
        scope=Scope.REQUEST,
        provides=IUsernameUniquenessChecker,
    )

    # Command handlers
    update_profile_handler: CompositeDependencySource = provide(
        UpdateProfileHandler, scope=Scope.REQUEST
    )
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
    get_customer_by_identity_handler: CompositeDependencySource = provide(
        GetCustomerByIdentityHandler, scope=Scope.REQUEST
    )
