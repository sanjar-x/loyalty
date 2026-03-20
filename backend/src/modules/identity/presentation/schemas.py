"""Pydantic request/response schemas for the Identity module API.

All schemas use CamelModel (camelCase JSON serialization) and include
field-level validation constraints.
"""

import uuid
from datetime import datetime
from typing import Self

from pydantic import EmailStr, Field, model_validator

from src.shared.schemas import CamelModel

# ---------------------------------------------------------------------------
# Authentication schemas
# ---------------------------------------------------------------------------


class RegisterRequest(CamelModel):
    """Request payload for identity registration.

    Attributes:
        email: A valid email address.
        password: Plaintext password (8-128 characters).
    """

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(CamelModel):
    """Response payload for successful registration.

    Attributes:
        identity_id: The newly created identity's UUID.
        message: Human-readable confirmation message.
    """

    identity_id: uuid.UUID
    message: str = "Registration successful"


class LoginRequest(CamelModel):
    """Request payload for email/password login.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password (max 128 characters).
    """

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(CamelModel):
    """Response payload containing an access/refresh token pair.

    Attributes:
        access_token: Short-lived JWT access token.
        refresh_token: Opaque refresh token for rotation.
        token_type: Token type (always "bearer").
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(CamelModel):
    """Request payload for token refresh.

    Attributes:
        refresh_token: The current opaque refresh token.
    """

    refresh_token: str = Field(..., min_length=1)


class LoginOIDCRequest(CamelModel):
    """Request payload for OIDC provider login.

    Attributes:
        provider_token: The token issued by the OIDC provider.
    """

    provider_token: str


class TelegramTokenResponse(CamelModel):
    """Response for Telegram Mini App authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool


# ---------------------------------------------------------------------------
# Account Management schemas
# ---------------------------------------------------------------------------


class ChangePasswordRequest(CamelModel):
    """Request payload for changing password.

    Attributes:
        current_password: The current password for verification.
        new_password: The new password (8-128 characters).
    """

    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------


class CreateRoleRequest(CamelModel):
    """Request payload for creating a custom role.

    Attributes:
        name: Unique role name (lowercase letters and underscores, 2-100 chars).
        description: Optional human-readable description (max 500 chars).
    """

    name: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)


class CreateRoleResponse(CamelModel):
    """Response payload for successful role creation.

    Attributes:
        role_id: The newly created role's UUID.
        message: Human-readable confirmation message.
    """

    role_id: uuid.UUID
    message: str = "Role created"


class AssignRoleRequest(CamelModel):
    """Request payload for assigning a role to an identity.

    Attributes:
        role_id: The UUID of the role to assign.
    """

    role_id: uuid.UUID


class MessageResponse(CamelModel):
    """Generic response payload with a human-readable message.

    Attributes:
        message: The response message.
    """

    message: str


# ---------------------------------------------------------------------------
# Admin Identity schemas
# ---------------------------------------------------------------------------


class AdminIdentityResponse(CamelModel):
    """Response payload for a single identity in a paginated list.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: User's first name.
        last_name: User's last name.
        phone: User's phone number, if available.
        roles: List of role names.
        created_at: When the identity was created.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    roles: list[str]
    created_at: datetime


class AdminIdentityListResponse(CamelModel):
    """Response payload for a paginated list of identities.

    Attributes:
        items: List of identity items for the current page.
        total: Total number of matching identities.
        offset: Current offset.
        limit: Page size.
    """

    items: list[AdminIdentityResponse]
    total: int
    offset: int
    limit: int


class RoleInfoResponse(CamelModel):
    """Response payload for role info attached to an identity detail.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional role description.
        is_system: Whether this is a system-managed role.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool


class AdminIdentityDetailResponse(CamelModel):
    """Response payload for a single identity's full detail.

    Attributes:
        identity_id: The identity's UUID.
        email: Login email (None for OIDC-only).
        auth_type: Authentication method (LOCAL or OIDC).
        is_active: Whether the identity is currently active.
        first_name: User's first name.
        last_name: User's last name.
        phone: User's phone number, if available.
        roles: List of role info objects.
        created_at: When the identity was created.
        deactivated_at: When the identity was deactivated, if applicable.
        deactivated_by: Identity ID of admin who deactivated, if applicable.
    """

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str | None
    last_name: str | None
    phone: str | None
    roles: list[RoleInfoResponse]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None


# ---------------------------------------------------------------------------
# Admin Deactivation schemas
# ---------------------------------------------------------------------------


class AdminDeactivateRequest(CamelModel):
    """Request payload for admin identity deactivation.

    Attributes:
        reason: Human-readable reason for deactivation (1-200 chars).
    """

    reason: str = Field(..., min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Role Management schemas
# ---------------------------------------------------------------------------


class UpdateRoleRequest(CamelModel):
    """Request payload for updating a role's name and/or description.

    At least one field must be provided.

    Attributes:
        name: New role name (lowercase letters and underscores, 2-100 chars).
        description: New role description (max 500 chars).
    """

    name: str | None = Field(None, min_length=2, max_length=100, pattern=r"^[a-z_]+$")
    description: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        """Validate that at least one field is provided."""
        if self.name is None and self.description is None:
            raise ValueError("At least one field (name or description) must be provided")
        return self


class SetRolePermissionsRequest(CamelModel):
    """Request payload for setting role permissions (full replace).

    Attributes:
        permission_ids: Complete set of permission IDs to assign.
    """

    permission_ids: list[uuid.UUID]


class PermissionDetailResponse(CamelModel):
    """Response payload for a permission detail in a role.

    Attributes:
        id: The permission's UUID.
        codename: Permission codename in 'resource:action' format.
        resource: The resource component of the codename.
        action: The action component of the codename.
        description: Optional human-readable description.
    """

    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


class RoleDetailResponse(CamelModel):
    """Response payload for a single role's full detail.

    Attributes:
        id: The role's UUID.
        name: The role's display name.
        description: Optional role description.
        is_system: Whether this is a system-managed role.
        permissions: List of permission detail objects.
    """

    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionDetailResponse]


# ---------------------------------------------------------------------------
# Permission schemas
# ---------------------------------------------------------------------------


class PermissionInfoResponse(CamelModel):
    """Response payload for a permission info in a grouped list.

    Attributes:
        id: The permission's UUID.
        codename: Permission codename in 'resource:action' format.
        resource: The resource component of the codename.
        action: The action component of the codename.
        description: Optional human-readable description.
    """

    id: uuid.UUID
    codename: str
    resource: str
    action: str
    description: str | None


class PermissionGroupResponse(CamelModel):
    """Response payload for a group of permissions sharing the same resource.

    Attributes:
        resource: The resource name.
        permissions: List of permissions for this resource.
    """

    resource: str
    permissions: list[PermissionInfoResponse]


# ---------------------------------------------------------------------------
# Staff Management schemas
# ---------------------------------------------------------------------------


class StaffListItemResponse(CamelModel):
    """Response for a staff member in a paginated list."""

    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime


class StaffListResponse(CamelModel):
    """Paginated staff list response."""

    items: list[StaffListItemResponse]
    total: int
    offset: int
    limit: int


class StaffDetailResponse(CamelModel):
    """Full staff member detail response."""

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    position: str | None
    department: str | None
    roles: list[RoleInfoResponse]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
    invited_by: uuid.UUID


# ---------------------------------------------------------------------------
# Staff Invitation schemas
# ---------------------------------------------------------------------------


class InviteStaffRequest(CamelModel):
    """Request to invite a new staff member."""

    email: EmailStr
    role_ids: list[uuid.UUID] = Field(..., min_length=1)


class InviteStaffResponse(CamelModel):
    """Response after creating a staff invitation."""

    invitation_id: uuid.UUID
    invite_url: str


class InvitationListItemResponse(CamelModel):
    """Response for an invitation in a paginated list."""

    id: uuid.UUID
    email: str
    status: str
    invited_by_email: str | None
    roles: list[str]
    created_at: datetime
    expires_at: datetime


class InvitationListResponse(CamelModel):
    """Paginated invitation list response."""

    items: list[InvitationListItemResponse]
    total: int
    offset: int
    limit: int


class InvitationInfoResponse(CamelModel):
    """Response with invitation details for the accept form."""

    email: str
    roles: list[str]
    expires_at: datetime


class AcceptInvitationRequest(CamelModel):
    """Request to accept a staff invitation."""

    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field("", max_length=100)
    last_name: str = Field("", max_length=100)


# ---------------------------------------------------------------------------
# Customer Management schemas
# ---------------------------------------------------------------------------


class CustomerListItemResponse(CamelModel):
    """Response for a customer in a paginated list."""

    identity_id: uuid.UUID
    email: str | None
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str | None
    roles: list[str]
    is_active: bool
    created_at: datetime


class CustomerListResponse(CamelModel):
    """Paginated customer list response."""

    items: list[CustomerListItemResponse]
    total: int
    offset: int
    limit: int


class CustomerDetailResponse(CamelModel):
    """Full customer detail response."""

    identity_id: uuid.UUID
    email: str | None
    auth_type: str
    is_active: bool
    first_name: str
    last_name: str
    phone: str | None
    referral_code: str | None
    referred_by: uuid.UUID | None
    roles: list[RoleInfoResponse]
    created_at: datetime
    deactivated_at: datetime | None
    deactivated_by: uuid.UUID | None
