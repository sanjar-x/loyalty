# tests/unit/shared/test_schemas.py
"""Tests for shared CamelModel base class."""

from src.shared.schemas import CamelModel


class SampleModel(CamelModel):
    first_name: str
    last_name: str
    is_active: bool = True


class TestCamelModel:
    def test_generates_camel_case_aliases(self):
        m = SampleModel(first_name="John", last_name="Doe")
        data = m.model_dump(by_alias=True)
        assert "firstName" in data
        assert "lastName" in data
        assert "isActive" in data

    def test_accepts_snake_case_with_populate_by_name(self):
        m = SampleModel(first_name="John", last_name="Doe")
        assert m.first_name == "John"
        assert m.last_name == "Doe"

    def test_accepts_camel_case_input(self):
        m = SampleModel.model_validate({
            "firstName": "Jane",
            "lastName": "Doe",
            "isActive": False,
        })
        assert m.first_name == "Jane"
        assert m.last_name == "Doe"
        assert m.is_active is False

    def test_model_dump_snake_case_by_default(self):
        m = SampleModel(first_name="A", last_name="B")
        data = m.model_dump()
        assert "first_name" in data
        assert "last_name" in data
