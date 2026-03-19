"""Structural tests for the SKU router.

Validates route registration, HTTP methods, paths, and status codes
without making actual HTTP calls.
"""

import pytest
from fastapi import status
from fastapi.routing import APIRoute

from src.modules.catalog.presentation.router_skus import sku_router


def _get_routes() -> list[APIRoute]:
    """Return all APIRoute entries from the sku_router."""
    return [r for r in sku_router.routes if isinstance(r, APIRoute)]


_PREFIX = "/products/{product_id}/skus"


def _find_route(path_suffix: str, method: str) -> APIRoute | None:
    """Find a route by its path suffix and HTTP method.

    The ``path_suffix`` is appended to the router prefix to build the full
    path stored on the ``APIRoute`` object.
    """
    full_path = f"{_PREFIX}{path_suffix}"
    for route in _get_routes():
        if route.path == full_path and method.upper() in route.methods:
            return route
    return None


class TestSKURouterStructure:
    """Structural tests: route count, prefix, tags."""

    def test_router_has_expected_number_of_routes(self) -> None:
        """Router registers exactly 4 routes (POST, GET, PUT, DELETE)."""
        routes = _get_routes()
        assert len(routes) == 4

    def test_router_prefix(self) -> None:
        """Router prefix is /products/{product_id}/skus."""
        assert sku_router.prefix == "/products/{product_id}/skus"

    def test_router_tags(self) -> None:
        """Router is tagged with 'SKUs'."""
        assert "SKUs" in sku_router.tags


class TestCreateSKURoute:
    """POST /products/{product_id}/skus."""

    def test_route_exists(self) -> None:
        """POST route is registered."""
        route = _find_route("", "POST")
        assert route is not None

    def test_status_code_is_201(self) -> None:
        """POST returns 201 Created."""
        route = _find_route("", "POST")
        assert route is not None
        assert route.status_code == status.HTTP_201_CREATED

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route("", "POST")
        assert route is not None
        assert route.name == "create_sku"


class TestListSKUsRoute:
    """GET /products/{product_id}/skus."""

    def test_route_exists(self) -> None:
        """GET route is registered."""
        route = _find_route("", "GET")
        assert route is not None

    def test_status_code_is_200(self) -> None:
        """GET returns 200 OK."""
        route = _find_route("", "GET")
        assert route is not None
        assert route.status_code == status.HTTP_200_OK

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route("", "GET")
        assert route is not None
        assert route.name == "list_skus"


class TestUpdateSKURoute:
    """PUT /products/{product_id}/skus/{sku_id}."""

    def test_route_exists(self) -> None:
        """PUT route is registered."""
        route = _find_route("/{sku_id}", "PUT")
        assert route is not None

    def test_status_code_is_200(self) -> None:
        """PUT returns 200 OK."""
        route = _find_route("/{sku_id}", "PUT")
        assert route is not None
        assert route.status_code == status.HTTP_200_OK

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route("/{sku_id}", "PUT")
        assert route is not None
        assert route.name == "update_sku"


class TestDeleteSKURoute:
    """DELETE /products/{product_id}/skus/{sku_id}."""

    def test_route_exists(self) -> None:
        """DELETE route is registered."""
        route = _find_route("/{sku_id}", "DELETE")
        assert route is not None

    def test_status_code_is_204(self) -> None:
        """DELETE returns 204 No Content."""
        route = _find_route("/{sku_id}", "DELETE")
        assert route is not None
        assert route.status_code == status.HTTP_204_NO_CONTENT

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route("/{sku_id}", "DELETE")
        assert route is not None
        assert route.name == "delete_sku"


class TestRouterHttpMethods:
    """Verify that only expected HTTP methods are registered."""

    @pytest.mark.parametrize(
        ("path", "expected_methods"),
        [
            (f"{_PREFIX}", {"POST", "GET"}),
            (f"{_PREFIX}/{{sku_id}}", {"PUT", "DELETE"}),
        ],
    )
    def test_only_expected_methods_on_path(self, path: str, expected_methods: set[str]) -> None:
        """Each path only has the expected HTTP methods registered."""
        routes = _get_routes()
        actual_methods: set[str] = set()
        for route in routes:
            if route.path == path:
                actual_methods.update(route.methods)
        assert actual_methods == expected_methods
