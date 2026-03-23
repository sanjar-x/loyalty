# tests/factories/orm_factories.py
"""Polyfactory-based ORM model factories for integration test data seeding."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from src.modules.catalog.infrastructure.models import (
    Brand as BrandModel,
)
from src.modules.catalog.infrastructure.models import (
    Category as CategoryModel,
)
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    LocalCredentialsModel,
    RoleModel,
    SessionModel,
)


class IdentityModelFactory(SQLAlchemyFactory):
    __model__ = IdentityModel
    __set_relationships__ = True


class CredentialsModelFactory(SQLAlchemyFactory):
    __model__ = LocalCredentialsModel
    __set_relationships__ = True


class SessionModelFactory(SQLAlchemyFactory):
    __model__ = SessionModel
    __set_relationships__ = True


class RoleModelFactory(SQLAlchemyFactory):
    __model__ = RoleModel
    __set_relationships__ = True


class BrandModelFactory(SQLAlchemyFactory):
    __model__ = BrandModel
    __set_relationships__ = True


class CategoryModelFactory(SQLAlchemyFactory):
    __model__ = CategoryModel
    __set_relationships__ = True
