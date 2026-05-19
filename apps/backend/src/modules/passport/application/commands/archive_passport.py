"""Command: customer archives a Passport (soft delete).

Orders that reference an archived passport keep their
``passport_snapshot`` (snapshot is JSONB on the order row) and their
FK is preserved via ``ON DELETE SET NULL``-equivalent — see Order
migration. Archival therefore never loses order history.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from src.modules.passport.domain.exceptions import (
    PassportNotFoundError,
    PassportOwnershipMismatchError,
)
from src.modules.passport.domain.interfaces import IPassportRepository
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class ArchivePassportCommand:
    passport_id: uuid.UUID
    identity_id: uuid.UUID


class ArchivePassportHandler:
    def __init__(
        self,
        repo: IPassportRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="ArchivePassportHandler")

    async def handle(self, command: ArchivePassportCommand) -> None:
        async with self._uow:
            passport = await self._repo.get_for_update(command.passport_id)
            if passport is None:
                raise PassportNotFoundError(passport_id=str(command.passport_id))
            if passport.identity_id != command.identity_id:
                raise PassportOwnershipMismatchError(
                    passport_id=str(command.passport_id)
                )
            passport.archive()
            await self._repo.update(passport)
            self._uow.register_aggregate(passport)
            await self._uow.commit()
            self._logger.info(
                "passport.archived",
                passport_id=str(passport.id),
                identity_id=str(command.identity_id),
            )
