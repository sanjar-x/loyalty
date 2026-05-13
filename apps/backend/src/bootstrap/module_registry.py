"""Bounded-context module registry.

Each bounded context exposes a single :class:`ModuleManifest` constant
in its ``src/modules/<name>/module.py`` file that declares everything
the bootstrap composition root needs to wire it in:

* DI providers,
* presentation routers (split into customer / admin / webhooks
  audiences so that :mod:`src.api.router` keeps the structural
  contract enforced by ``tests/architecture/test_router_audience.py``),
* dotted-path strings for TaskIQ task modules whose import side-effects
  register ``@broker.task`` handlers and outbox event handlers.

The single source of truth for the order of registration is
:data:`MODULES`. Adding a new bounded context requires:

1. Creating ``src/modules/<name>/module.py`` with a
   :class:`ModuleManifest` constant.
2. Appending it to :data:`MODULES`.

Everything else (Dishka container, FastAPI router aggregation, TaskIQ
worker / scheduler bootstrap, integration-test container) iterates
over :data:`MODULES` automatically.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass, field

from dishka import Provider
from fastapi import APIRouter


@dataclass(frozen=True)
class ModuleManifest:
    """Declarative registration of one bounded-context module.

    Attributes:
        name: Stable identifier (``"order"``, ``"referral"``, ...). Used
            as the discriminator in architectural-fitness whitelists and
            in observability dashboards.
        providers: Dishka providers to register in the application
            container. Order matters when providers reuse one another's
            bindings — module authors arrange them locally and the
            bootstrap loop preserves declaration order.
        customer_routers: Routers mounted under ``/api/v1/<resource>``
            (storefront / customer-facing endpoints).
        admin_routers: Routers mounted under ``/api/v1/admin/...``.
        webhook_routers: Routers mounted under ``/api/v1/webhooks/...``.
        task_modules: Dotted-path strings for modules whose import
            side-effects register TaskIQ tasks and outbox event handlers
            (every ``@broker.task`` and ``register_event_handler`` call).
            Imported lazily by ``import_task_modules`` so that the
            container is configured before tasks are wired.
    """

    name: str
    providers: Sequence[Provider] = field(default_factory=tuple)
    customer_routers: Sequence[APIRouter] = field(default_factory=tuple)
    admin_routers: Sequence[APIRouter] = field(default_factory=tuple)
    webhook_routers: Sequence[APIRouter] = field(default_factory=tuple)
    task_modules: Sequence[str] = field(default_factory=tuple)

    @property
    def routers(self) -> tuple[APIRouter, ...]:
        """All routers, in audience order: customer → admin → webhooks."""
        return (
            *self.customer_routers,
            *self.admin_routers,
            *self.webhook_routers,
        )


def import_task_modules(manifests: Sequence[ModuleManifest]) -> None:
    """Import each manifest's ``task_modules`` so they register handlers.

    The TaskIQ broker stores ``@broker.task`` registrations at import
    time; the outbox relay's ``register_event_handler`` is also a side
    effect of importing the module that calls it. Centralising the
    discovery here avoids hard-coding the list across web / worker /
    scheduler bootstraps.
    """
    for manifest in manifests:
        for dotted_path in manifest.task_modules:
            importlib.import_module(dotted_path)
