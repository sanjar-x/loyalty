"""Structural tests for the Product Attributes router.

Validates route registration, HTTP methods, paths, and status codes
without making actual HTTP calls.
"""

import pytest
from fastapi import status
from fastapi.routing import APIRoute

from src.modules.catalog.presentation.router_product_attributes import (
    product_attribute_router,
)


def _get_routes() -> list[APIRoute]:
    """Return all APIRoute entries from the product_attribute_router."""
    return [r for r in product_attribute_router.routes if isinstance(r, APIRoute)]


BASE_PATH = "/products/{product_id}/attributes"


def _find_route(path: str, method: str) -> APIRoute | None:
    """Find a route by its full path and HTTP method."""
    for route in _get_routes():
        if route.path == path and method.upper() in route.methods:
            return route
    return None


class TestProductAttributeRouterStructure:
    """Structural tests: route count, methods, paths, status codes."""

    def test_router_has_expected_number_of_routes(self) -> None:
        """Router registers exactly 3 routes (POST, GET, DELETE)."""
        routes = _get_routes()
        assert len(routes) == 3

    def test_router_prefix(self) -> None:
        """Router prefix is /products/{product_id}/attributes."""
        assert product_attribute_router.prefix == "/products/{product_id}/attributes"

    def test_router_tags(self) -> None:
        """Router is tagged with 'Product Attributes'."""
        assert "Product Attributes" in product_attribute_router.tags


class TestAssignProductAttributeRoute:
    """POST /products/{product_id}/attributes."""

    def test_route_exists(self) -> None:
        """POST route is registered."""
        route = _find_route(BASE_PATH, "POST")
        assert route is not None

    def test_status_code_is_201(self) -> None:
        """POST returns 201 Created."""
        route = _find_route(BASE_PATH, "POST")
        assert route is not None
        assert route.status_code == status.HTTP_201_CREATED

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route(BASE_PATH, "POST")
        assert route is not None
        assert route.name == "assign_product_attribute"


class TestListProductAttributesRoute:
    """GET /products/{product_id}/attributes."""

    def test_route_exists(self) -> None:
        """GET route is registered."""
        route = _find_route(BASE_PATH, "GET")
        assert route is not None

    def test_status_code_is_200(self) -> None:
        """GET returns 200 OK."""
        route = _find_route(BASE_PATH, "GET")
        assert route is not None
        assert route.status_code == status.HTTP_200_OK

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route(BASE_PATH, "GET")
        assert route is not None
        assert route.name == "list_product_attributes"


class TestRemoveProductAttributeRoute:
    """DELETE /products/{product_id}/attributes/{attribute_id}."""

    DELETE_PATH = f"{BASE_PATH}/{{attribute_id}}"

    def test_route_exists(self) -> None:
        """DELETE route is registered."""
        route = _find_route(self.DELETE_PATH, "DELETE")
        assert route is not None

    def test_status_code_is_204(self) -> None:
        """DELETE returns 204 No Content."""
        route = _find_route(self.DELETE_PATH, "DELETE")
        assert route is not None
        assert route.status_code == status.HTTP_204_NO_CONTENT

    def test_route_name(self) -> None:
        """Route function name matches the endpoint function."""
        route = _find_route(self.DELETE_PATH, "DELETE")
        assert route is not None
        assert route.name == "remove_product_attribute"


class TestRouterHttpMethods:
    """Verify that only expected HTTP methods are registered."""

    @pytest.mark.parametrize(
        ("path", "expected_methods"),
        [
            (BASE_PATH, {"POST", "GET"}),
            (f"{BASE_PATH}/{{attribute_id}}", {"DELETE"}),
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
