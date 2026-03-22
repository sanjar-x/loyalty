"""SQLAlchemy declarative base with consistent naming conventions.

Defines the shared ``Base`` class and ``MetaData`` used by all ORM models
across every bounded-context module.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base.

    All ORM models inherit from this class to share a single ``MetaData``
    instance with unified naming conventions for indexes, constraints,
    and foreign keys.
    """

    metadata = metadata

    def __repr__(self) -> str:
        """Return a developer-friendly representation of the model instance."""
        columns = ", ".join([
            f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_")
        ])
        return f"<{self.__class__.__name__}({columns})>"
