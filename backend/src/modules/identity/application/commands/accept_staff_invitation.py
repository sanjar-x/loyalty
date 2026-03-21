"""Command handler for accepting a staff invitation."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.identity.domain.entities import (
    Identity,
    LocalCredentials,
    Session,
    StaffInvitation,
)
from src.modules.identity.domain.events import IdentityRegisteredEvent
from src.modules.identity.domain.exceptions import (
    IdentityAlreadyExistsError,
    InvitationNotFoundError,
)
from src.modules.identity.domain.interfaces import (
    IIdentityRepository,
    IRoleRepository,
    ISessionRepository,
    IStaffInvitationRepository,
)
from src.modules.identity.domain.value_objects import AccountType
from src.shared.exceptions import ConflictError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.security import IPasswordHasher, ITokenProvider
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AcceptStaffInvitationCommand:
    """Command to accept a staff invitation.

    Attributes:
        raw_token: The raw invitation token from the URL.
        password: Password for the new staff account.
        first_name: Staff member's first name.
        last_name: Staff member's last name.
        ip_address: Client IP address for session.
        user_agent: Client User-Agent for session.
    """

    raw_token: str
    password: str
    first_name: str
    last_name: str
    ip_address: str
    user_agent: str


@dataclass(frozen=True)
class AcceptStaffInvitationResult:
    """Result of accepting a staff invitation.

    Attributes:
        access_token: JWT access token.
        refresh_token: Opaque refresh token.
        identity_id: The new staff identity's UUID.
    """

    access_token: str
    refresh_token: str
    identity_id: uuid.UUID


class AcceptStaffInvitationHandler:
    """Handles staff invitation acceptance with identity creation."""

    def __init__(
        self,
        invitation_repo: IStaffInvitationRepository,
        identity_repo: IIdentityRepository,
        role_repo: IRoleRepository,
        session_repo: ISessionRepository,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        token_provider: ITokenProvider,
        logger: ILogger,
    ) -> None:
        self._invitation_repo = invitation_repo
        self._identity_repo = identity_repo
        self._role_repo = role_repo
        self._session_repo = session_repo
        self._uow = uow
        self._hasher = hasher
        self._token_provider = token_provider
        self._logger = logger.bind(handler="AcceptStaffInvitationHandler")

    async def handle(self, command: AcceptStaffInvitationCommand) -> AcceptStaffInvitationResult:
        """Execute the accept invitation command.

        Creates Identity (STAFF), credentials, assigns roles, marks invitation
        accepted, creates session, and returns tokens.

        Args:
            command: The acceptance command.

        Returns:
            Result with tokens and identity ID.

        Raises:
            InvitationNotFoundError: If the token is invalid.
            InvitationExpiredError: If the invitation has expired.
            InvitationAlreadyAcceptedError: If already accepted.
            InvitationRevokedError: If revoked.
        """
        # Hash password outside UoW to avoid holding DB connection during CPU work
        password_hash = self._hasher.hash(command.password)

        async with self._uow:
            # Find invitation by token hash
            token_hash = StaffInvitation.hash_token(command.raw_token)
            invitation = await self._invitation_repo.get_by_token_hash(token_hash)
            if invitation is None:
                raise InvitationNotFoundError()

            # Validate invitation FIRST (status + expiry) — fail fast before side effects
            identity = Identity.register_staff()
            invitation.accept(identity.id)
            await self._invitation_repo.update(invitation)

            # Persist identity and credentials (only after invitation is validated)
            now = datetime.now(UTC)
            credentials = LocalCredentials(
                identity_id=identity.id,
                email=invitation.email,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
            await self._identity_repo.add(identity)
            await self._identity_repo.add_credentials(credentials)

            # Assign pre-defined roles (validate each still exists)
            for role_id in invitation.role_ids:
                role = await self._role_repo.get(role_id)
                if role is not None:
                    await self._role_repo.assign_to_identity(
                        identity_id=identity.id,
                        role_id=role_id,
                    )

            # Create session (use freshly queried roles, not stale invitation data)
            raw_refresh, _ = self._token_provider.create_refresh_token()
            role_ids = await self._role_repo.get_identity_role_ids(identity.id)
            session = Session.create(
                identity_id=identity.id,
                refresh_token=raw_refresh,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                role_ids=role_ids,
            )
            await self._session_repo.add(session)
            await self._session_repo.add_session_roles(session.id, role_ids)

            # Create access token
            access_token = self._token_provider.create_access_token(
                payload_data={
                    "sub": str(identity.id),
                    "sid": str(session.id),
                },
            )

            # Emit IdentityRegisteredEvent for StaffMember creation
            identity.add_domain_event(
                IdentityRegisteredEvent(
                    identity_id=identity.id,
                    email=invitation.email,
                    account_type=AccountType.STAFF.value,
                    aggregate_id=str(identity.id),
                )
            )
            self._uow.register_aggregate(identity)
            self._uow.register_aggregate(invitation)

            try:
                await self._uow.commit()
            except ConflictError:
                # TOCTOU: concurrent invitation acceptance with the same email
                # passed validation but hit the DB unique constraint
                raise IdentityAlreadyExistsError() from None

        self._logger.info(
            "staff.invitation.accepted",
            identity_id=str(identity.id),
            invitation_id=str(invitation.id),
            email=invitation.email,
        )
        return AcceptStaffInvitationResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            identity_id=identity.id,
        )
