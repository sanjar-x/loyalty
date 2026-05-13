"""Unit tests for cursor pagination utilities."""

import uuid

import pytest

from src.shared.pagination import CursorPage, decode_cursor, encode_cursor


class TestEncodeDecode:
    """Cursor encode / decode round-trip tests."""

    def test_round_trip_int_sort(self):
        sort_val = 42
        pk = uuid.uuid4()
        cursor = encode_cursor(sort_val, pk)
        decoded_sort, decoded_pk = decode_cursor(cursor)
        assert decoded_sort == sort_val
        assert decoded_pk == pk

    def test_round_trip_string_sort(self):
        sort_val = "2024-06-15T10:30:00"
        pk = uuid.uuid4()
        cursor = encode_cursor(sort_val, pk)
        decoded_sort, decoded_pk = decode_cursor(cursor)
        assert decoded_sort == sort_val
        assert decoded_pk == pk

    def test_round_trip_float_sort(self):
        sort_val = 99.5
        pk = uuid.uuid4()
        cursor = encode_cursor(sort_val, pk)
        decoded_sort, decoded_pk = decode_cursor(cursor)
        assert decoded_sort == sort_val
        assert decoded_pk == pk

    def test_round_trip_none_sort(self):
        sort_val = None
        pk = uuid.uuid4()
        cursor = encode_cursor(sort_val, pk)
        decoded_sort, decoded_pk = decode_cursor(cursor)
        assert decoded_sort is None
        assert decoded_pk == pk

    def test_round_trip_zero_sort(self):
        sort_val = 0
        pk = uuid.uuid4()
        cursor = encode_cursor(sort_val, pk)
        decoded_sort, decoded_pk = decode_cursor(cursor)
        assert decoded_sort == sort_val
        assert decoded_pk == pk

    def test_decode_invalid_base64_raises(self):
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor("not-base64!!!")

    def test_decode_invalid_json_raises(self):
        import base64

        bad_cursor = base64.urlsafe_b64encode(b"not json").decode()
        with pytest.raises(ValueError, match="Invalid cursor"):
            decode_cursor(bad_cursor)

    def test_cursor_is_url_safe(self):
        """Cursor string should not contain characters needing URL encoding."""
        cursor = encode_cursor(12345, uuid.uuid4())
        assert "+" not in cursor
        assert "/" not in cursor


class TestCursorPage:
    """Tests for the CursorPage data model."""

    def test_empty_page(self):
        page: CursorPage[str] = CursorPage(items=[], has_next=False)
        assert page.items == []
        assert page.has_next is False
        assert page.next_cursor is None
        assert page.total is None

    def test_page_with_items_and_cursor(self):
        page: CursorPage[int] = CursorPage(
            items=[1, 2, 3],
            has_next=True,
            next_cursor="abc123",
            total=100,
        )
        assert len(page.items) == 3
        assert page.has_next is True
        assert page.next_cursor == "abc123"
        assert page.total == 100
