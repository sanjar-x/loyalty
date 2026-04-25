"""SQLAlchemy-backed repository for ``Variable``."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.exceptions import (
    VariableCodeTakenError,
    VariableValidationError,
)
from src.modules.pricing.domain.interfaces import (
    IVariableRepository,
    VariableListFilter,
)
from src.modules.pricing.domain.value_objects import VariableDataType, VariableScope
from src.modules.pricing.infrastructure.models import VariableModel


class VariableRepository(IVariableRepository):
    """Data Mapper repository for the ``Variable`` aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: VariableModel) -> Variable:
        variable = Variable(
            id=model.id,
            code=model.code,
            scope=VariableScope(model.scope),
            data_type=VariableDataType(model.data_type),
            unit=model.unit,
            name=dict(model.name or {}),
            description=dict(model.description or {}),
            is_required=model.is_required,
            default_value=model.default_value,
            is_system=model.is_system,
            is_fx_rate=model.is_fx_rate,
            is_user_editable_at_runtime=model.is_user_editable_at_runtime,
            max_age_days=model.max_age_days,
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        variable.clear_domain_events()
        return variable

    @staticmethod
    def _apply(model: VariableModel, variable: Variable) -> None:
        # Only mutable fields (code/scope/data_type/unit/is_fx_rate are not touched here —
        # the application layer refuses PATCH attempts that change them).
        model.name = dict(variable.name)
        model.description = dict(variable.description)
        model.is_required = variable.is_required
        model.default_value = variable.default_value
        model.max_age_days = variable.max_age_days
        model.version_lock = variable.version_lock
        model.updated_by = variable.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(self, variable: Variable) -> Variable:
        model = VariableModel(
            id=variable.id,
            code=variable.code,
            scope=variable.scope.value,
            data_type=variable.data_type.value,
            unit=variable.unit,
            name=dict(variable.name),
            description=dict(variable.description),
            is_required=variable.is_required,
            default_value=variable.default_value,
            is_system=variable.is_system,
            is_fx_rate=variable.is_fx_rate,
            is_user_editable_at_runtime=variable.is_user_editable_at_runtime,
            max_age_days=variable.max_age_days,
            version_lock=variable.version_lock,
            updated_by=variable.updated_by,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            # Most likely cause: duplicate code (unique constraint).
            raise VariableCodeTakenError(code=variable.code) from exc
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(self, variable: Variable) -> Variable:
        model = await self._session.get(VariableModel, variable.id)
        if model is None:
            msg = f"Variable {variable.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != variable.version_lock - 1:
            raise VariableValidationError(
                message=(
                    "Variable was modified concurrently; expected version "
                    f"{variable.version_lock - 1}, got {model.version_lock}."
                ),
                error_code="PRICING_VARIABLE_VERSION_CONFLICT",
                details={
                    "variable_id": str(variable.id),
                    "expected_version": variable.version_lock - 1,
                    "actual_version": model.version_lock,
                },
            )

        self._apply(model, variable)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, variable_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(VariableModel).where(VariableModel.id == variable_id)
        )
        await self._session.flush()

    async def get_by_id(self, variable_id: uuid.UUID) -> Variable | None:
        model = await self._session.get(VariableModel, variable_id)
        return self._to_domain(model) if model else None

    async def get_by_code(self, code: str) -> Variable | None:
        stmt = select(VariableModel).where(VariableModel.code == code)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list(self, filters: VariableListFilter | None = None) -> list[Variable]:
        stmt = select(VariableModel).order_by(VariableModel.code.asc())
        if filters is not None:
            if filters.scope is not None:
                stmt = stmt.where(VariableModel.scope == filters.scope.value)
            if filters.is_system is not None:
                stmt = stmt.where(VariableModel.is_system.is_(filters.is_system))
            if filters.is_fx_rate is not None:
                stmt = stmt.where(VariableModel.is_fx_rate.is_(filters.is_fx_rate))
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]
