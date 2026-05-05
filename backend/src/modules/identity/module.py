"""Bootstrap manifest for the identity bounded context.

Identity provides authn / authz primitives plus the staff-invitation
flow and the customer / staff admin lookup endpoints. The customer-
side ``/auth`` and ``/account`` routers are separate from the
``/invitations`` router (which is role-agnostic — both staff onboarding
and customer-side OIDC flows hit it) and from the ``/admin`` family.
"""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.identity.infrastructure.provider import IdentityProvider
from src.modules.identity.presentation.router_account import identity_account_router
from src.modules.identity.presentation.router_admin import admin_router
from src.modules.identity.presentation.router_auth import auth_router
from src.modules.identity.presentation.router_customers import customer_admin_router
from src.modules.identity.presentation.router_invitation import invitation_router
from src.modules.identity.presentation.router_staff import staff_admin_router

IDENTITY_MODULE = ModuleManifest(
    name="identity",
    providers=(IdentityProvider(),),
    customer_routers=(
        auth_router,
        invitation_router,
        identity_account_router,
    ),
    admin_routers=(
        admin_router,
        staff_admin_router,
        customer_admin_router,
    ),
    task_modules=("src.modules.identity.application.consumers.role_events",),
)
