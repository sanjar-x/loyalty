"""Bootstrap manifest for the passport bounded context (ADR-011, Sprint 1.5 Part 2)."""

from src.bootstrap.module_registry import ModuleManifest
from src.modules.passport.infrastructure.provider import PassportProvider
from src.modules.passport.presentation.router_passports import passport_router

PASSPORT_MODULE = ModuleManifest(
    name="passport",
    providers=(PassportProvider(),),
    customer_routers=(passport_router,),
)
