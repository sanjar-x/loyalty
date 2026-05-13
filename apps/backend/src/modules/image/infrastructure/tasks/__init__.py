"""Image module TaskIQ task registry.

Only the rmbg task body still lives inside backend (see :mod:`.rmbg`).
The storage task bodies (``process_image_task`` /
``cleanup_orphans_task``) moved out of backend in Phase 5b and now live
under ``apps/workers/image/storage/tasks.py`` — that worker registers
them on its broker; backend only dispatches via
``broker.kicker().with_task_name("process_image").kiq(...)``.

The package-level ``__init__`` re-exports ``remove_background_task``
for the rmbg dispatcher in ``router_admin.py``; the storage tasks are
deliberately NOT re-exported because backend has no business holding a
reference to bodies it doesn't own.

IMPORTANT: importing this ``__init__`` pulls in ``.rmbg`` which, when
``BG_REMOVAL_ENABLED=true``, registers the rmbg task on the broker.
Workers that must NOT subscribe to the ``image.ml`` queue should avoid
importing this package — backend's HTTP routers do, but only the
``apps/workers/image/rmbg`` deployment enables the flag in env.
"""

from src.modules.image.infrastructure.tasks.rmbg import remove_background_task

__all__ = ["remove_background_task"]
