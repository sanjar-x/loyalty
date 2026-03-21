"""Dishka dependency injection provider for the Identity module.

Registers all repository implementations, command handlers, and query handlers
at REQUEST scope. The LoginHandler factory method injects configuration values
from application settings.
"""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.bootstrap.config import settings
from src.infrastructure.security.telegram import TelegramInitDataValidator
from src.modules.identity.application.commands.accept_staff_invitation import (
    AcceptStaffInvitationHandler,
)
from src.modules.identity.application.commands.admin_deactivate_identity import (
    AdminDeactivateIdentityHandler,
)
from src.modules.identity.application.commands.assign_role import AssignRoleHandler
from src.modules.identity.application.commands.create_role import CreateRoleHandler
from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityHandler,
)
from src.modules.identity.application.commands.delete_role import DeleteRoleHandler
from src.modules.identity.application.commands.invite_staff import InviteStaffHandler
from src.modules.identity.application.commands.login import LoginHandler
from src.modules.identity.application.commands.login_telegram import LoginTelegramHandler
from src.modules.identity.application.commands.logout import LogoutHandler
from src.modules.identity.application.commands.logout_all import LogoutAllHandler
from src.modules.identity.application.commands.reactivate_identity import (
    ReactivateIdentityHandler,
)
from src.modules.identity.application.commands.refresh_token import RefreshTokenHandler
from src.modules.identity.application.commands.register import RegisterHandler
from src.modules.identity.application.commands.revoke_role import RevokeRoleHandler
from src.modules.identity.application.commands.revoke_staff_invitation import (
    RevokeStaffInvitationHandler,
)
from src.modules.identity.application.commands.set_role_permissions import (
    SetRolePermissionsHandler,
)
from src.modules.identity.application.commands.update_role import UpdateRoleHandler
from src.modules.identity.application.queries.get_customer_detail import (
    GetCustomerDetailHandler,
)
from src.modules.identity.application.queries.get_identity_detail import (
    GetIdentityDetailHandler,
)
from src.modules.identity.application.queries.get_identity_roles import (
    GetIdentityRolesHandler,
)
from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
)
from src.modules.identity.application.queries.get_role_detail import (
    GetRoleDetailHandler,
)
from src.modules.identity.application.queries.get_session_permissions import (
    GetSessionPermissionsHandler,
)
from src.modules.identity.application.queries.get_staff_detail import (
    GetStaffDetailHandler,
)
from src.modules.identity.application.queries.list_customers import (
    ListCustomersHandler,
)
from src.modules.identity.application.queries.list_identities import (
    ListIdentitiesHandler,
)
from src.modules.identity.application.queries.list_permissions import (
    ListPermissionsHandler,
)
from src.modules.identity.application.queries.list_roles import ListRolesHandler
from src.modules.identity.application.queries.list_staff import ListStaffHandler
from src.modules.identity.application.queries.list_staff_invitations import (
    ListStaffInvitationsHandler,
)
from src.modules.identity.application.queries.validate_invitation import (
    ValidateInvitationHandler,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ILinkedAccountRepository,
    IPermissionRepository,
    IRoleRepository,
    ISessionRepository,
    IStaffInvitationRepository,
    ITelegramInitDataValidator,
)
from src.modules.identity.infrastructure.repositories.identity_repository import (
    IdentityRepository,
)
from src.modules.identity.infrastructure.repositories.linked_account_repository import (
    LinkedAccountRepository,
)
from src.modules.identity.infrastructure.repositories.permission_repository import (
    PermissionRepository,
)
from src.modules.identity.infrastructure.repositories.role_repository import (
    RoleRepository,
)
from src.modules.identity.infrastructure.repositories.session_repository import (
    SessionRepository,
)
from src.modules.identity.infrastructure.repositories.staff_invitation_repository import (
    StaffInvitationRepository,
)
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, IPermissionResolver, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


class IdentityProvider(Provider):
    """Dishka provider that wires all Identity module dependencies."""

    # Repositories (REQUEST scope)
    identity_repo: CompositeDependencySource = provide(
        IdentityRepository, scope=Scope.REQUEST, provides=IIdentityRepository
    )
    session_repo: CompositeDependencySource = provide(
        SessionRepository, scope=Scope.REQUEST, provides=ISessionRepository
    )
    role_repo: CompositeDependencySource = provide(
        RoleRepository, scope=Scope.REQUEST, provides=IRoleRepository
    )
    permission_repo: CompositeDependencySource = provide(
        PermissionRepository, scope=Scope.REQUEST, provides=IPermissionRepository
    )
    linked_account_repo: CompositeDependencySource = provide(
        LinkedAccountRepository, scope=Scope.REQUEST, provides=ILinkedAccountRepository
    )
    staff_invitation_repo: CompositeDependencySource = provide(
        StaffInvitationRepository, scope=Scope.REQUEST, provides=IStaffInvitationRepository
    )

    @provide(scope=Scope.REQUEST)
    def telegram_validator(self) -> ITelegramInitDataValidator:
        return TelegramInitDataValidator(
            bot_token=settings.BOT_TOKEN.get_secret_value(),
            max_age=settings.TELEGRAM_INIT_DATA_MAX_AGE,
        )

    @provide(scope=Scope.REQUEST)
    def login_telegram_handler(
        self,
        telegram_validator: ITelegramInitDataValidator,
        linked_account_repo: ILinkedAccountRepository,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        token_provider: ITokenProvider,
        permission_resolver: IPermissionResolver,
        logger: ILogger,
    ) -> LoginTelegramHandler:
        return LoginTelegramHandler(
            telegram_validator=telegram_validator,
            linked_account_repo=linked_account_repo,
            identity_repo=identity_repo,
            session_repo=session_repo,
            role_repo=role_repo,
            uow=uow,
            token_provider=token_provider,
            permission_resolver=permission_resolver,
            logger=logger,
            max_sessions=settings.MAX_ACTIVE_SESSIONS_PER_IDENTITY,
            refresh_token_days=settings.TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS,
            idle_timeout_minutes=settings.TELEGRAM_SESSION_IDLE_TIMEOUT_MINUTES,
        )

    # Command handlers (REQUEST scope)
    register_handler: CompositeDependencySource = provide(RegisterHandler, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def login_handler(
        self,
        identity_repo: IIdentityRepository,
        session_repo: ISessionRepository,
        role_repo: IRoleRepository,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        token_provider: ITokenProvider,
        logger: ILogger,
    ) -> LoginHandler:
        """Create a LoginHandler with configuration-driven session limits.

        Args:
            identity_repo: Identity repository.
            session_repo: Session repository.
            role_repo: Role repository.
            uow: Unit of work.
            hasher: Password hasher.
            token_provider: Token provider.
            logger: Structured logger.

        Returns:
            A configured LoginHandler instance.
        """
        return LoginHandler(
            identity_repo=identity_repo,
            session_repo=session_repo,
            role_repo=role_repo,
            uow=uow,
            hasher=hasher,
            token_provider=token_provider,
            logger=logger,
            max_sessions=settings.MAX_ACTIVE_SESSIONS_PER_IDENTITY,
            refresh_token_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
            idle_timeout_minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES,
        )

    refresh_token_handler: CompositeDependencySource = provide(
        RefreshTokenHandler, scope=Scope.REQUEST
    )
    logout_handler: CompositeDependencySource = provide(LogoutHandler, scope=Scope.REQUEST)
    logout_all_handler: CompositeDependencySource = provide(LogoutAllHandler, scope=Scope.REQUEST)
    create_role_handler: CompositeDependencySource = provide(CreateRoleHandler, scope=Scope.REQUEST)
    delete_role_handler: CompositeDependencySource = provide(DeleteRoleHandler, scope=Scope.REQUEST)
    assign_role_handler: CompositeDependencySource = provide(AssignRoleHandler, scope=Scope.REQUEST)
    revoke_role_handler: CompositeDependencySource = provide(RevokeRoleHandler, scope=Scope.REQUEST)
    deactivate_identity_handler: CompositeDependencySource = provide(
        DeactivateIdentityHandler, scope=Scope.REQUEST
    )

    # Admin command handlers
    admin_deactivate_handler: CompositeDependencySource = provide(
        AdminDeactivateIdentityHandler, scope=Scope.REQUEST
    )
    reactivate_handler: CompositeDependencySource = provide(
        ReactivateIdentityHandler, scope=Scope.REQUEST
    )
    update_role_handler: CompositeDependencySource = provide(UpdateRoleHandler, scope=Scope.REQUEST)
    set_role_permissions_handler: CompositeDependencySource = provide(
        SetRolePermissionsHandler, scope=Scope.REQUEST
    )

    # Query handlers (REQUEST scope)
    get_session_permissions_handler: CompositeDependencySource = provide(
        GetSessionPermissionsHandler, scope=Scope.REQUEST
    )
    get_my_sessions_handler: CompositeDependencySource = provide(
        GetMySessionsHandler, scope=Scope.REQUEST
    )
    list_roles_handler: CompositeDependencySource = provide(ListRolesHandler, scope=Scope.REQUEST)
    list_permissions_handler: CompositeDependencySource = provide(
        ListPermissionsHandler, scope=Scope.REQUEST
    )
    get_identity_roles_handler: CompositeDependencySource = provide(
        GetIdentityRolesHandler, scope=Scope.REQUEST
    )

    # Admin query handlers
    list_identities_handler: CompositeDependencySource = provide(
        ListIdentitiesHandler, scope=Scope.REQUEST
    )
    get_identity_detail_handler: CompositeDependencySource = provide(
        GetIdentityDetailHandler, scope=Scope.REQUEST
    )
    get_role_detail_handler: CompositeDependencySource = provide(
        GetRoleDetailHandler, scope=Scope.REQUEST
    )

    # Staff invitation command handlers
    invite_staff_handler: CompositeDependencySource = provide(
        InviteStaffHandler, scope=Scope.REQUEST
    )
    accept_staff_invitation_handler: CompositeDependencySource = provide(
        AcceptStaffInvitationHandler, scope=Scope.REQUEST
    )
    revoke_staff_invitation_handler: CompositeDependencySource = provide(
        RevokeStaffInvitationHandler, scope=Scope.REQUEST
    )

    # Staff/Customer query handlers
    list_staff_handler: CompositeDependencySource = provide(ListStaffHandler, scope=Scope.REQUEST)
    get_staff_detail_handler: CompositeDependencySource = provide(
        GetStaffDetailHandler, scope=Scope.REQUEST
    )
    list_customers_handler: CompositeDependencySource = provide(
        ListCustomersHandler, scope=Scope.REQUEST
    )
    get_customer_detail_handler: CompositeDependencySource = provide(
        GetCustomerDetailHandler, scope=Scope.REQUEST
    )
    list_staff_invitations_handler: CompositeDependencySource = provide(
        ListStaffInvitationsHandler, scope=Scope.REQUEST
    )
    validate_invitation_handler: CompositeDependencySource = provide(
        ValidateInvitationHandler, scope=Scope.REQUEST
    )
