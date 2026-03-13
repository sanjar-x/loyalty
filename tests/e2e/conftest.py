from unittest.mock import patch

import pytest
from dishka import AsyncContainer
from httpx import ASGITransport, AsyncClient

from src.bootstrap.web import create_app


@pytest.fixture(scope="session")
def fastapi_app(app_container: AsyncContainer):
    with patch("src.bootstrap.web.create_container", return_value=app_container):
        app = create_app()
        yield app


@pytest.fixture(scope="session")
async def async_client(fastapi_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        yield client
