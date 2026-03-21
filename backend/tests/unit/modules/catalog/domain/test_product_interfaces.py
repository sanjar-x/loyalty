# tests/unit/modules/catalog/domain/test_product_interfaces.py
"""Tests for IProductRepository and IProductAttributeValueRepository interfaces.

Covers:
- IProductRepository extends ICatalogRepository[DomainProduct]
- IProductRepository has all 6 abstract methods with correct signatures
- IProductAttributeValueRepository is a standalone ABC with 5 abstract methods
- Cannot instantiate abstract classes directly (abstractness enforced)
- Domain purity: no framework imports in interfaces.py
"""

import ast
import inspect
import pathlib
from abc import ABC
from typing import ClassVar, get_args, get_origin

import pytest

from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.interfaces import (
    ICatalogRepository,
    IProductAttributeValueRepository,
    IProductRepository,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INTERFACES_FILE = pathlib.Path("src/modules/catalog/domain/interfaces.py")

FORBIDDEN_FRAMEWORK_IMPORTS = [
    "sqlalchemy",
    "fastapi",
    "pydantic",
    "redis",
    "dishka",
    "taskiq",
    "alembic",
]


def _get_imports_from_source(filepath: pathlib.Path) -> list[str]:
    """Return all imported module names from a Python source file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _get_abstract_method_names(cls: type) -> set[str]:
    """Return names of all abstract methods on a class (own + inherited)."""
    return {
        name
        for name, member in inspect.getmembers(cls)
        if getattr(member, "__isabstractmethod__", False)
    }


def _concrete_subclass(*abstract_methods: str) -> type:
    """Dynamically build a minimal concrete subclass that implements the given methods."""

    async def _stub(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        ...

    namespace = {method: _stub for method in abstract_methods}
    return type("_Concrete", tuple(), namespace)


# ---------------------------------------------------------------------------
# IProductRepository — inheritance
# ---------------------------------------------------------------------------


class TestIProductRepositoryInheritance:
    """IProductRepository must extend ICatalogRepository[DomainProduct]."""

    def test_is_subclass_of_icatalog_repository(self) -> None:
        """IProductRepository inherits from ICatalogRepository."""
        assert issubclass(IProductRepository, ICatalogRepository)

    def test_is_subclass_of_abc(self) -> None:
        """IProductRepository is abstract (inherits from ABC via ICatalogRepository)."""
        assert issubclass(IProductRepository, ABC)

    def test_generic_parameter_is_domain_product(self) -> None:
        """ICatalogRepository is parameterised with DomainProduct, not Any."""
        # Inspect __orig_bases__ to find the generic base and its type arg.
        orig_bases = getattr(IProductRepository, "__orig_bases__", ())
        catalog_base = None
        for base in orig_bases:
            if get_origin(base) is ICatalogRepository:
                catalog_base = base
                break
        assert catalog_base is not None, (
            "IProductRepository does not directly parameterise ICatalogRepository"
        )
        args = get_args(catalog_base)
        assert len(args) == 1, "Expected exactly one type argument"
        assert args[0] is DomainProduct, (
            f"Expected ICatalogRepository[DomainProduct], got ICatalogRepository[{args[0]}]"
        )

    def test_not_any_as_type_parameter(self) -> None:
        """The generic parameter must not be typing.Any."""
        from typing import Any

        orig_bases = getattr(IProductRepository, "__orig_bases__", ())
        for base in orig_bases:
            if get_origin(base) is ICatalogRepository:
                args = get_args(base)
                assert args[0] is not Any, (
                    "IProductRepository still uses ICatalogRepository[Any] — must be [DomainProduct]"
                )


# ---------------------------------------------------------------------------
# IProductRepository — abstract methods
# ---------------------------------------------------------------------------


class TestIProductRepositoryAbstractMethods:
    """IProductRepository must declare the 6 additional abstract methods."""

    EXPECTED_METHODS: ClassVar[set[str]] = {
        "get_by_slug",
        "check_slug_exists",
        "check_slug_exists_excluding",
        "get_for_update",
        "get_with_skus",
        "list_products",
    }

    # CRUD methods inherited from ICatalogRepository
    INHERITED_CRUD: ClassVar[set[str]] = {"add", "get", "update", "delete"}

    def test_all_six_methods_are_abstract(self) -> None:
        """Every required method is registered as abstract."""
        abstract_methods = _get_abstract_method_names(IProductRepository)
        missing = self.EXPECTED_METHODS - abstract_methods
        assert not missing, f"Missing abstract methods: {missing}"

    def test_inherits_crud_methods_as_abstract(self) -> None:
        """CRUD methods from ICatalogRepository are also abstract on IProductRepository."""
        abstract_methods = _get_abstract_method_names(IProductRepository)
        missing_crud = self.INHERITED_CRUD - abstract_methods
        assert not missing_crud, f"Missing inherited CRUD abstract methods: {missing_crud}"

    def test_cannot_instantiate_directly(self) -> None:
        """Direct instantiation of IProductRepository raises TypeError."""
        with pytest.raises(TypeError):
            IProductRepository()  # type: ignore[abstract]

    # --- Individual method signature checks ---

    def test_get_by_slug_signature(self) -> None:
        """get_by_slug(self, slug: str) -> DomainProduct | None."""
        method = IProductRepository.get_by_slug
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "slug" in params, "get_by_slug must have 'slug' parameter"
        assert len(params) == 2, f"Expected (self, slug), got {params}"  # self + slug

    def test_check_slug_exists_signature(self) -> None:
        """check_slug_exists(self, slug: str) -> bool."""
        method = IProductRepository.check_slug_exists
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "slug" in params, "check_slug_exists must have 'slug' parameter"
        assert len(params) == 2

    def test_check_slug_exists_excluding_signature(self) -> None:
        """check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool."""
        method = IProductRepository.check_slug_exists_excluding
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "slug" in params, "check_slug_exists_excluding must have 'slug' parameter"
        assert "exclude_id" in params, (
            "check_slug_exists_excluding must have 'exclude_id' parameter"
        )
        assert len(params) == 3  # self + slug + exclude_id

    def test_get_for_update_signature(self) -> None:
        """get_for_update(self, product_id: uuid.UUID) -> DomainProduct | None."""
        method = IProductRepository.get_for_update
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "product_id" in params, "get_for_update must have 'product_id' parameter"
        assert len(params) == 2

    def test_get_with_skus_signature(self) -> None:
        """get_with_skus(self, product_id: uuid.UUID) -> DomainProduct | None."""
        method = IProductRepository.get_with_skus
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "product_id" in params, "get_with_skus must have 'product_id' parameter"
        assert len(params) == 2

    def test_list_products_signature(self) -> None:
        """list_products(self, limit, offset, status=None, brand_id=None) -> tuple[list, int]."""
        method = IProductRepository.list_products
        sig = inspect.signature(method)
        params = sig.parameters
        assert "limit" in params, "list_products must have 'limit' parameter"
        assert "offset" in params, "list_products must have 'offset' parameter"
        assert "status" in params, "list_products must have 'status' parameter"
        assert "brand_id" in params, "list_products must have 'brand_id' parameter"

    def test_list_products_optional_status_defaults_to_none(self) -> None:
        """list_products 'status' parameter must default to None."""
        sig = inspect.signature(IProductRepository.list_products)
        status_param = sig.parameters["status"]
        assert status_param.default is None, (
            f"'status' must default to None, got {status_param.default!r}"
        )

    def test_list_products_optional_brand_id_defaults_to_none(self) -> None:
        """list_products 'brand_id' parameter must default to None."""
        sig = inspect.signature(IProductRepository.list_products)
        brand_id_param = sig.parameters["brand_id"]
        assert brand_id_param.default is None, (
            f"'brand_id' must default to None, got {brand_id_param.default!r}"
        )

    def test_all_methods_are_coroutines(self) -> None:
        """All abstract methods on IProductRepository must be async (coroutine functions)."""
        for method_name in self.EXPECTED_METHODS | self.INHERITED_CRUD:
            method = getattr(IProductRepository, method_name)
            assert inspect.iscoroutinefunction(method), (
                f"IProductRepository.{method_name} must be an async method"
            )


# ---------------------------------------------------------------------------
# IProductAttributeValueRepository — standalone ABC
# ---------------------------------------------------------------------------


class TestIProductAttributeValueRepositoryBase:
    """IProductAttributeValueRepository must be a standalone ABC (not ICatalogRepository)."""

    def test_is_subclass_of_abc(self) -> None:
        """IProductAttributeValueRepository inherits from ABC."""
        assert issubclass(IProductAttributeValueRepository, ABC)

    def test_is_not_subclass_of_icatalog_repository(self) -> None:
        """IProductAttributeValueRepository is standalone — does NOT extend ICatalogRepository."""
        assert not issubclass(IProductAttributeValueRepository, ICatalogRepository), (
            "IProductAttributeValueRepository must be a standalone ABC, "
            "not a subclass of ICatalogRepository"
        )

    def test_cannot_instantiate_directly(self) -> None:
        """Direct instantiation raises TypeError."""
        with pytest.raises(TypeError):
            IProductAttributeValueRepository()  # type: ignore[abstract]


class TestIProductAttributeValueRepositoryAbstractMethods:
    """IProductAttributeValueRepository must declare exactly 5 abstract methods."""

    EXPECTED_METHODS: ClassVar[set[str]] = {"add", "get", "delete", "list_by_product", "exists"}

    def test_all_five_methods_are_abstract(self) -> None:
        """Every required method is registered as abstract."""
        abstract_methods = _get_abstract_method_names(IProductAttributeValueRepository)
        missing = self.EXPECTED_METHODS - abstract_methods
        assert not missing, f"Missing abstract methods: {missing}"

    def test_exactly_five_abstract_methods(self) -> None:
        """No extra abstract methods beyond the planned 5."""
        abstract_methods = _get_abstract_method_names(IProductAttributeValueRepository)
        extra = abstract_methods - self.EXPECTED_METHODS
        assert not extra, (
            f"Unexpected extra abstract methods on IProductAttributeValueRepository: {extra}"
        )

    # --- Individual signature checks ---

    def test_add_signature(self) -> None:
        """add(self, entity: DomainProductAttributeValue) -> DomainProductAttributeValue."""
        sig = inspect.signature(IProductAttributeValueRepository.add)
        params = list(sig.parameters.keys())
        assert "entity" in params, "add must have 'entity' parameter"
        assert len(params) == 2  # self + entity

    def test_get_signature(self) -> None:
        """get(self, pav_id: uuid.UUID) -> DomainProductAttributeValue | None."""
        sig = inspect.signature(IProductAttributeValueRepository.get)
        params = list(sig.parameters.keys())
        assert "pav_id" in params, "get must have 'pav_id' parameter"
        assert len(params) == 2

    def test_delete_signature(self) -> None:
        """delete(self, pav_id: uuid.UUID) -> None."""
        sig = inspect.signature(IProductAttributeValueRepository.delete)
        params = list(sig.parameters.keys())
        assert "pav_id" in params, "delete must have 'pav_id' parameter"
        assert len(params) == 2

    def test_list_by_product_signature(self) -> None:
        """list_by_product(self, product_id: uuid.UUID) -> list[DomainProductAttributeValue]."""
        sig = inspect.signature(IProductAttributeValueRepository.list_by_product)
        params = list(sig.parameters.keys())
        assert "product_id" in params, "list_by_product must have 'product_id' parameter"
        assert len(params) == 2

    def test_exists_takes_product_id_and_attribute_id(self) -> None:
        """exists(self, product_id, attribute_id) — duplicate guard requires both keys."""
        sig = inspect.signature(IProductAttributeValueRepository.exists)
        params = list(sig.parameters.keys())
        assert "product_id" in params, "exists must have 'product_id' parameter"
        assert "attribute_id" in params, "exists must have 'attribute_id' parameter"
        assert len(params) == 3  # self + product_id + attribute_id

    def test_all_methods_are_coroutines(self) -> None:
        """All abstract methods on IProductAttributeValueRepository must be async."""
        for method_name in self.EXPECTED_METHODS:
            method = getattr(IProductAttributeValueRepository, method_name)
            assert inspect.iscoroutinefunction(method), (
                f"IProductAttributeValueRepository.{method_name} must be an async method"
            )


# ---------------------------------------------------------------------------
# Concrete subclass instantiation (verifies contract completeness)
# ---------------------------------------------------------------------------


class TestConcreteSubclassInstantiation:
    """A concrete subclass that implements all abstract methods must be instantiable."""

    def test_concrete_product_repo_instantiates(self) -> None:
        """A fully-implemented IProductRepository subclass can be instantiated."""

        class ConcreteProductRepo(IProductRepository):
            async def add(self, entity): ...

            async def get(self, entity_id): ...

            async def update(self, entity): ...

            async def delete(self, entity_id): ...

            async def get_by_slug(self, slug): ...

            async def check_slug_exists(self, slug): ...

            async def check_slug_exists_excluding(self, slug, exclude_id): ...

            async def get_for_update(self, product_id): ...

            async def get_with_skus(self, product_id): ...

            async def list_products(self, limit, offset, status=None, brand_id=None): ...

        instance = ConcreteProductRepo()
        assert isinstance(instance, IProductRepository)

    def test_partial_product_repo_cannot_instantiate(self) -> None:
        """A subclass missing any abstract method cannot be instantiated."""

        class PartialProductRepo(IProductRepository):
            # Intentionally omits all methods — should fail
            pass

        with pytest.raises(TypeError):
            PartialProductRepo()  # type: ignore[abstract]

    def test_concrete_pav_repo_instantiates(self) -> None:
        """A fully-implemented IProductAttributeValueRepository subclass can be instantiated."""

        class ConcretePAVRepo(IProductAttributeValueRepository):
            async def add(self, entity): ...

            async def get(self, pav_id): ...

            async def delete(self, pav_id): ...

            async def list_by_product(self, product_id): ...

            async def exists(self, product_id, attribute_id): ...

        instance = ConcretePAVRepo()
        assert isinstance(instance, IProductAttributeValueRepository)

    def test_partial_pav_repo_cannot_instantiate(self) -> None:
        """A subclass of IProductAttributeValueRepository missing methods raises TypeError."""

        class PartialPAVRepo(IProductAttributeValueRepository):
            async def add(self, entity): ...

            # Missing: get, delete, list_by_product, exists

        with pytest.raises(TypeError):
            PartialPAVRepo()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Domain purity — no framework imports in interfaces.py
# ---------------------------------------------------------------------------


class TestDomainPurity:
    """interfaces.py must not import any infrastructure frameworks."""

    def test_no_sqlalchemy_imports(self) -> None:
        """interfaces.py must not import sqlalchemy."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        sql_imports = [imp for imp in imports if imp.startswith("sqlalchemy")]
        assert not sql_imports, f"interfaces.py imports sqlalchemy: {sql_imports}"

    def test_no_fastapi_imports(self) -> None:
        """interfaces.py must not import fastapi."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        fa_imports = [imp for imp in imports if imp.startswith("fastapi")]
        assert not fa_imports, f"interfaces.py imports fastapi: {fa_imports}"

    def test_no_pydantic_imports(self) -> None:
        """interfaces.py must not import pydantic."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        pd_imports = [imp for imp in imports if imp.startswith("pydantic")]
        assert not pd_imports, f"interfaces.py imports pydantic: {pd_imports}"

    def test_no_redis_imports(self) -> None:
        """interfaces.py must not import redis."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        redis_imports = [imp for imp in imports if imp.startswith("redis")]
        assert not redis_imports, f"interfaces.py imports redis: {redis_imports}"

    def test_no_dishka_imports(self) -> None:
        """interfaces.py must not import dishka."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        dishka_imports = [imp for imp in imports if imp.startswith("dishka")]
        assert not dishka_imports, f"interfaces.py imports dishka: {dishka_imports}"

    def test_no_any_in_typing_imports(self) -> None:
        """'Any' must not be imported from typing (replaced by DomainProduct)."""
        source = INTERFACES_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "typing":
                imported_names = [alias.name for alias in node.names]
                assert "Any" not in imported_names, (
                    "interfaces.py still imports 'Any' from typing — "
                    "IProductRepository should use ICatalogRepository[DomainProduct]"
                )

    @pytest.mark.parametrize("framework", FORBIDDEN_FRAMEWORK_IMPORTS)
    def test_no_framework_import(self, framework: str) -> None:
        """Parametrized: interfaces.py must not import any of the forbidden frameworks."""
        imports = _get_imports_from_source(INTERFACES_FILE)
        bad = [imp for imp in imports if imp.startswith(framework)]
        assert not bad, f"interfaces.py imports {framework}: {bad}"

    def test_only_stdlib_and_domain_imports(self) -> None:
        """interfaces.py only imports from stdlib and src.modules.catalog.domain.*"""
        imports = _get_imports_from_source(INTERFACES_FILE)
        allowed_prefixes = ("uuid", "abc", "typing", "src.modules.catalog.domain.")
        for imp in imports:
            assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
                f"Unexpected import in interfaces.py: '{imp}'. "
                f"Only stdlib and catalog.domain imports are permitted."
            )


# ---------------------------------------------------------------------------
# ICatalogRepository base — CRUD method presence (regression)
# ---------------------------------------------------------------------------


class TestICatalogRepositoryCRUD:
    """Regression: the CRUD base class retains its 4 abstract methods."""

    CRUD_METHODS: ClassVar[set[str]] = {"add", "get", "update", "delete"}

    def test_catalog_repository_has_four_crud_methods(self) -> None:
        abstract_methods = _get_abstract_method_names(ICatalogRepository)
        missing = self.CRUD_METHODS - abstract_methods
        assert not missing, f"ICatalogRepository is missing CRUD methods: {missing}"

    def test_catalog_repository_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            ICatalogRepository()  # type: ignore[abstract]
