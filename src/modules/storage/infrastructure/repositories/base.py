# src/modules/storage/infrastructure/repositories/base.py
import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Result, delete, insert, inspect
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.interfaces.entities import IBase

ModelType = TypeVar("ModelType", bound=IBase)

