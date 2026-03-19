# tests/factories/schema_factories.py
"""Polyfactory-based Pydantic schema factories for e2e test payloads."""

from polyfactory.factories.pydantic_factory import ModelFactory

from src.modules.catalog.presentation.schemas import (
    BrandCreateRequest,
    CategoryCreateRequest,
)
from src.modules.identity.presentation.schemas import (
    LoginRequest,
    RegisterRequest,
)


class RegisterRequestFactory(ModelFactory):
    __model__ = RegisterRequest


class LoginRequestFactory(ModelFactory):
    __model__ = LoginRequest


class BrandCreateRequestFactory(ModelFactory):
    __model__ = BrandCreateRequest


class CategoryCreateRequestFactory(ModelFactory):
    __model__ = CategoryCreateRequest
