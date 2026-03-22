"""SQLAlchemy ORM models for the Identity module.

Maps domain concepts to PostgreSQL tables using the Data Mapper pattern.
These models are infrastructure concerns and must never leak into the
domain or application layers.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base
from src.modules.identity.domain.value_objects import PrimaryAuthMethod


class IdentityModel(Base):
    """ORM model for the ``identities`` table (root entity for IAM)."""

    __tablename__ = "identities"
    __table_args__ = ({"comment": "Authentication identities (root entity for IAM)"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="PK (UUIDv7)",
    )
    primary_auth_method: Mapped[str] = mapped_column(
        Enum(PrimaryAuthMethod, native_enum=False, length=10),
        nullable=False,
        comment="Authentication method: LOCAL, OIDC, or TELEGRAM",
    )
    account_type: Mapped[str] = mapped_column(
        String(10),
        server_default="CUSTOMER",
        nullable=False,
        index=True,
        comment="Account type: CUSTOMER or STAFF",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("true"),
        nullable=False,
        index=True,
        comment="Whether identity can authenticate",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the identity was deactivated",
    )
    deactivated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Identity ID of admin who deactivated this identity (null=self)",
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        server_default=text("1"),
        nullable=False,
        comment="Incrementing version for instant JWT invalidation",
    )

    credentials: Mapped[LocalCredentialsModel | None] = relationship(
        back_populates="identity",
        uselist=False,
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="identity",
        cascade="all, delete-orphan",
    )
    linked_accounts: Mapped[list[LinkedAccountModel]] = relationship(
        back_populates="identity",
        cascade="all, delete-orphan",
    )


class LocalCredentialsModel(Base):
    """ORM model for the ``local_credentials`` table (email + password hash)."""

    __tablename__ = "local_credentials"
    __table_args__ = ({"comment": "Local auth credentials (email + password hash)"},)

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
        comment="PK + FK -> identities (Shared PK 1:1)",
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        comment="Login email (unique across system)",
    )
    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Argon2id (new) or Bcrypt (legacy) hash — 512 for non-default Argon2 params",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    identity: Mapped[IdentityModel] = relationship(back_populates="credentials")


class LinkedAccountModel(Base):
    """ORM model for the ``linked_accounts`` table (external OIDC providers)."""

    __tablename__ = "linked_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_sub_id", name="uq_linked_accounts_provider_sub"),
        {"comment": "External OIDC provider accounts linked to identities"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_sub_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
        comment="Whether provider verified this email",
    )
    provider_metadata: Mapped[dict] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
        comment="Provider-specific profile data",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    identity: Mapped[IdentityModel] = relationship(back_populates="linked_accounts")


class RoleModel(Base):
    """ORM model for the ``roles`` table (RBAC role definitions)."""

    __tablename__ = "roles"
    __table_args__ = ({"comment": "RBAC role definitions"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
        comment="System roles cannot be modified or deleted",
    )
    target_account_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Account type this role targets: CUSTOMER, STAFF, or NULL (any)",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    permissions: Mapped[list[PermissionModel]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
    )


class PermissionModel(Base):
    """ORM model for the ``permissions`` table (resource:action codenames)."""

    __tablename__ = "permissions"
    __table_args__ = ({"comment": "RBAC permissions (resource:action codenames)"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    codename: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Permission codename in resource:action format",
    )
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    roles: Mapped[list[RoleModel]] = relationship(
        secondary="role_permissions",
        back_populates="permissions",
    )


class RolePermissionModel(Base):
    """ORM model for the ``role_permissions`` association table."""

    __tablename__ = "role_permissions"
    __table_args__ = (Index("ix_role_permissions_role_id", "role_id"),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class RoleHierarchyModel(Base):
    """ORM model for the ``role_hierarchy`` table (role inheritance via CTE)."""

    __tablename__ = "role_hierarchy"
    __table_args__ = (
        CheckConstraint(
            "parent_role_id != child_role_id",
            name="ck_role_hierarchy_no_self_ref",
        ),
        {"comment": "Role inheritance: parent inherits all child permissions via CTE"},
    )

    parent_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class IdentityRoleModel(Base):
    """ORM model for the ``identity_roles`` association table."""

    __tablename__ = "identity_roles"
    __table_args__ = (
        Index("ix_identity_roles_identity_id", "identity_id"),
        Index("ix_identity_roles_role_id", "role_id"),
    )

    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Identity ID of admin who assigned this role",
    )


class SessionModel(Base):
    """ORM model for the ``sessions`` table (refresh token rotation)."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_identity_active", "identity_id", "is_revoked", "expires_at"),
        {"comment": "Authentication sessions with refresh token rotation"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    identity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="SHA-256 hash of opaque refresh token",
    )
    ip_address: Mapped[str | None] = mapped_column(
        INET(),
        nullable=True,
        comment="Client IP at session creation",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Client User-Agent",
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="Refresh token expiry (created_at + REFRESH_TOKEN_EXPIRE_DAYS)",
    )
    last_active_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last token refresh timestamp",
    )
    idle_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="Sliding idle timeout (extends on refresh)",
    )

    identity: Mapped[IdentityModel] = relationship(back_populates="sessions")
    activated_roles: Mapped[list[SessionRoleModel]] = relationship(
        cascade="all, delete-orphan",
    )


class SessionRoleModel(Base):
    """ORM model for the ``session_roles`` table (NIST session-role activation)."""

    __tablename__ = "session_roles"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )


class StaffInvitationModel(Base):
    """ORM model for the ``staff_invitations`` table."""

    __tablename__ = "staff_invitations"
    __table_args__ = (
        Index("ix_staff_invitations_email_status", "email", "status"),
        {"comment": "Staff member invitations with token-based acceptance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(10),
        server_default="PENDING",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    accepted_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identities.id"),
        nullable=True,
    )


class StaffInvitationRoleModel(Base):
    """ORM model for the ``staff_invitation_roles`` table (pre-assigned roles)."""

    __tablename__ = "staff_invitation_roles"

    invitation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_invitations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id"),
        primary_key=True,
    )
