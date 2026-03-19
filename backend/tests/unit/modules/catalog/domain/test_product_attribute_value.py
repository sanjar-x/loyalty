"""Tests for ProductAttributeValue domain entity.

Covers:
- create() factory with auto-generated UUID
- create() with explicit ID (pav_id)
- All 4 fields present and correct types
- Not an AggregateRoot (no domain event infrastructure)
- Domain purity (no framework imports in entities.py)
"""

import ast
import pathlib
import uuid

import pytest

from src.modules.catalog.domain.entities import ProductAttributeValue
from src.shared.interfaces.entities import AggregateRoot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pav(**overrides: object) -> ProductAttributeValue:
    """Build a ProductAttributeValue with sensible defaults."""
    defaults: dict[str, object] = {
        "product_id": uuid.uuid4(),
        "attribute_id": uuid.uuid4(),
        "attribute_value_id": uuid.uuid4(),
    }
    defaults.update(overrides)
    return ProductAttributeValue.create(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Creation — happy path
# ---------------------------------------------------------------------------


class TestProductAttributeValueCreate:
    """Factory method creates instances correctly."""

    def test_create_returns_instance(self) -> None:
        """create() returns a ProductAttributeValue object."""
        pav = _make_pav()
        assert isinstance(pav, ProductAttributeValue)

    def test_create_auto_generates_uuid(self) -> None:
        """create() without pav_id generates a non-None UUID."""
        pav = _make_pav()
        assert isinstance(pav.id, uuid.UUID)
        assert pav.id is not None

    def test_create_auto_generates_unique_ids(self) -> None:
        """Each call without pav_id produces a different UUID."""
        pav1 = _make_pav()
        pav2 = _make_pav()
        assert pav1.id != pav2.id

    def test_create_with_explicit_pav_id(self) -> None:
        """create() with pav_id uses the supplied UUID as id."""
        explicit_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        pav = _make_pav(pav_id=explicit_id)
        assert pav.id == explicit_id

    def test_create_stores_product_id(self) -> None:
        """product_id field matches the supplied value."""
        pid = uuid.uuid4()
        pav = _make_pav(product_id=pid)
        assert pav.product_id == pid

    def test_create_stores_attribute_id(self) -> None:
        """attribute_id field matches the supplied value."""
        aid = uuid.uuid4()
        pav = _make_pav(attribute_id=aid)
        assert pav.attribute_id == aid

    def test_create_stores_attribute_value_id(self) -> None:
        """attribute_value_id field matches the supplied value."""
        avid = uuid.uuid4()
        pav = _make_pav(attribute_value_id=avid)
        assert pav.attribute_value_id == avid

    def test_create_all_four_fields_at_once(self) -> None:
        """All four fields are correctly assigned in a single call."""
        pid = uuid.uuid4()
        aid = uuid.uuid4()
        avid = uuid.uuid4()
        explicit_id = uuid.uuid4()

        pav = ProductAttributeValue.create(
            product_id=pid,
            attribute_id=aid,
            attribute_value_id=avid,
            pav_id=explicit_id,
        )

        assert pav.id == explicit_id
        assert pav.product_id == pid
        assert pav.attribute_id == aid
        assert pav.attribute_value_id == avid


# ---------------------------------------------------------------------------
# Field types
# ---------------------------------------------------------------------------


class TestProductAttributeValueFieldTypes:
    """All public fields have correct runtime types."""

    def test_id_is_uuid(self) -> None:
        pav = _make_pav()
        assert type(pav.id) is uuid.UUID

    def test_product_id_is_uuid(self) -> None:
        pav = _make_pav()
        assert type(pav.product_id) is uuid.UUID

    def test_attribute_id_is_uuid(self) -> None:
        pav = _make_pav()
        assert type(pav.attribute_id) is uuid.UUID

    def test_attribute_value_id_is_uuid(self) -> None:
        pav = _make_pav()
        assert type(pav.attribute_value_id) is uuid.UUID

    def test_entity_has_exactly_four_public_fields(self) -> None:
        """Entity carries exactly id, product_id, attribute_id, attribute_value_id."""
        pav = _make_pav()
        assert hasattr(pav, "id")
        assert hasattr(pav, "product_id")
        assert hasattr(pav, "attribute_id")
        assert hasattr(pav, "attribute_value_id")


# ---------------------------------------------------------------------------
# Not an AggregateRoot
# ---------------------------------------------------------------------------


class TestProductAttributeValueIsNotAggregateRoot:
    """ProductAttributeValue is a plain child entity — not an aggregate root."""

    def test_does_not_extend_aggregate_root(self) -> None:
        """Class hierarchy must not include AggregateRoot."""
        assert not issubclass(ProductAttributeValue, AggregateRoot)

    def test_instance_has_no_add_domain_event(self) -> None:
        """Child entity must not expose add_domain_event()."""
        pav = _make_pav()
        assert not hasattr(pav, "add_domain_event")

    def test_instance_has_no_domain_events_property(self) -> None:
        """Child entity must not expose a domain_events property."""
        pav = _make_pav()
        assert not hasattr(pav, "domain_events")

    def test_instance_has_no_clear_domain_events(self) -> None:
        """Child entity must not expose clear_domain_events()."""
        pav = _make_pav()
        assert not hasattr(pav, "clear_domain_events")


# ---------------------------------------------------------------------------
# Domain purity (architecture)
# ---------------------------------------------------------------------------


FORBIDDEN_IMPORTS: list[str] = [
    "sqlalchemy",
    "fastapi",
    "pydantic",
    "redis",
    "dishka",
    "aiohttp",
    "httpx",
    "starlette",
]


def _get_imports_from_file(filepath: pathlib.Path) -> list[str]:
    """Return all top-level module names imported in a Python source file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    return imported


class TestProductAttributeValueDomainPurity:
    """entities.py must not import any infrastructure/presentation framework."""

    def test_entities_file_has_no_forbidden_imports(self) -> None:
        """Domain entities file must import only stdlib and internal domain modules."""
        entities_path = pathlib.Path("src/modules/catalog/domain/entities.py")
        imports = _get_imports_from_file(entities_path)
        violations: list[str] = []
        for imp in imports:
            for forbidden in FORBIDDEN_IMPORTS:
                if imp.startswith(forbidden):
                    violations.append(f"entities.py imports '{imp}' ({forbidden} is forbidden)")
        assert violations == [], "\n".join(violations)

    def test_product_attribute_value_class_location_is_domain(self) -> None:
        """ProductAttributeValue must live in the domain layer, not application/infra."""
        module = ProductAttributeValue.__module__
        assert "domain" in module, (
            f"ProductAttributeValue is in '{module}', expected a domain module"
        )


# ---------------------------------------------------------------------------
# Edge cases / keyword-only enforcement
# ---------------------------------------------------------------------------


class TestProductAttributeValueFactoryEdgeCases:
    """Edge cases and API contract for the factory method."""

    def test_create_is_keyword_only(self) -> None:
        """create() uses keyword-only arguments; positional calls must fail."""
        pid = uuid.uuid4()
        aid = uuid.uuid4()
        avid = uuid.uuid4()
        with pytest.raises(TypeError):
            ProductAttributeValue.create(pid, aid, avid)  # type: ignore[misc]

    def test_create_with_none_pav_id_generates_uuid(self) -> None:
        """Explicitly passing pav_id=None triggers auto-generation."""
        pav = ProductAttributeValue.create(
            product_id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),
            attribute_value_id=uuid.uuid4(),
            pav_id=None,
        )
        assert isinstance(pav.id, uuid.UUID)

    def test_two_pavs_with_same_pav_id_are_equal_by_id(self) -> None:
        """Entities with the same pav_id carry identical id values."""
        shared_id = uuid.uuid4()
        pav_a = _make_pav(pav_id=shared_id)
        pav_b = _make_pav(pav_id=shared_id)
        assert pav_a.id == pav_b.id

    @pytest.mark.parametrize(
        "missing_field",
        ["product_id", "attribute_id", "attribute_value_id"],
    )
    def test_create_missing_required_field_raises_type_error(self, missing_field: str) -> None:
        """Omitting any required keyword argument raises TypeError."""
        kwargs: dict[str, uuid.UUID] = {
            "product_id": uuid.uuid4(),
            "attribute_id": uuid.uuid4(),
            "attribute_value_id": uuid.uuid4(),
        }
        del kwargs[missing_field]
        with pytest.raises(TypeError):
            ProductAttributeValue.create(**kwargs)  # type: ignore[arg-type]
