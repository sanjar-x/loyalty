"""Telegram bot entry point for the ``apps/bot`` deployable artefact.

Wires the Aiogram ``Bot`` + ``Dispatcher`` (built by
``src.bot.factory.create_dispatcher``) to the Dishka DI container produced
by ``src.bootstrap.container.create_container`` and starts long-polling.
The factory itself does the heavy lifting (FSM storage, middleware chain,
router registration); this module is just the lifecycle harness.

Run command:

    python -m telegram_bot.main

Not currently deployed — the corresponding Railway service has not been
provisioned yet. The artefact is ready for the day it is.
"""

from __future__ import annotations

import asyncio

from src.bootstrap.config import settings
from src.bootstrap.container import create_container
from src.bot.factory import create_bot, create_dispatcher


async def run() -> None:
    """Build the bot + dispatcher and start long-polling."""
    container = create_container()
    bot = create_bot(settings)
    dispatcher = create_dispatcher(container=container, settings=settings)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await container.close()
        await bot.session.close()


def main() -> None:
    """Synchronous entry point — runs the async ``run`` coroutine."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
