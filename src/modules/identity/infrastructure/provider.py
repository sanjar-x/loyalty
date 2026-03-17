# src/modules/identity/infrastructure/provider.py
from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.bootstrap.config import settings
from src.modules.identity.application.commands.assign_role import AssignRoleHandler
from src.modules.identity.application.commands.create_role import CreateRoleHandler
from src.modules.identity.application.commands.deactivate_identity import (
    DeactivateIdentityHandler,
)
from src.modules.identity.application.commands.delete_role import DeleteRoleHandler
from src.modules.identity.application.commands.login import LoginHandler
from src.modules.identity.application.commands.logout import LogoutHandler
from src.modules.identity.application.commands.logout_all import LogoutAllHandler
from src.modules.identity.application.commands.refresh_token import RefreshTokenHandler
from src.modules.identity.application.commands.register import RegisterHandler
from src.modules.identity.application.commands.revoke_role import RevokeRoleHandler
from src.modules.identity.application.queries.get_identity_roles import (
    GetIdentityRolesHandler,
)
from src.modules.identity.application.queries.get_my_sessions import (
    GetMySessionsHandler,
)
from src.modules.identity.application.queries.get_session_permissions import (
    GetSessionPermissionsHandler,
)
from src.modules.identity.application.queries.list_permissions import (
    ListPermissionsHandler,
)
from src.modules.identity.application.queries.list_roles import ListRolesHandler
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    ILinkedAccountRepository,
    IPermissionRepository,
    IRoleRepository,
    ISessionRepository,
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
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


class IdentityProvider(Provider):
    # --- Repositories (REQUEST scope) ---
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

    # --- Command Handlers (REQUEST scope) ---
    register_handler: CompositeDependencySource = provide(
        RegisterHandler, scope=Scope.REQUEST
    )

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
        )

    refresh_token_handler: CompositeDependencySource = provide(
        RefreshTokenHandler, scope=Scope.REQUEST
    )
    logout_handler: CompositeDependencySource = provide(
        LogoutHandler, scope=Scope.REQUEST
    )
    logout_all_handler: CompositeDependencySource = provide(
        LogoutAllHandler, scope=Scope.REQUEST
    )
    create_role_handler: CompositeDependencySource = provide(
        CreateRoleHandler, scope=Scope.REQUEST
    )
    delete_role_handler: CompositeDependencySource = provide(
        DeleteRoleHandler, scope=Scope.REQUEST
    )
    assign_role_handler: CompositeDependencySource = provide(
        AssignRoleHandler, scope=Scope.REQUEST
    )
    revoke_role_handler: CompositeDependencySource = provide(
        RevokeRoleHandler, scope=Scope.REQUEST
    )
    deactivate_identity_handler: CompositeDependencySource = provide(
        DeactivateIdentityHandler, scope=Scope.REQUEST
    )

    # --- Query Handlers (REQUEST scope) ---
    get_session_permissions_handler: CompositeDependencySource = provide(
        GetSessionPermissionsHandler, scope=Scope.REQUEST
    )
    get_my_sessions_handler: CompositeDependencySource = provide(
        GetMySessionsHandler, scope=Scope.REQUEST
    )
    list_roles_handler: CompositeDependencySource = provide(
        ListRolesHandler, scope=Scope.REQUEST
    )
    list_permissions_handler: CompositeDependencySource = provide(
        ListPermissionsHandler, scope=Scope.REQUEST
    )
    get_identity_roles_handler: CompositeDependencySource = provide(
        GetIdentityRolesHandler, scope=Scope.REQUEST
    )
