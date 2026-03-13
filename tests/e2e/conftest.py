# tests/e2e/conftest.py
from collections.abc import AsyncIterable
from unittest.mock import patch

import pytest
from dishka import AsyncContainer
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.bootstrap.web import create_app

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
async def fastapi_app(app_container: AsyncContainer) -> FastAPI:
    with patch("src.bootstrap.web.create_container", return_value=app_container):
        app = create_app()
        yield app


@pytest.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncIterable[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
