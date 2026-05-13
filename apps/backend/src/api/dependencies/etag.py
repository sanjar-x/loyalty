"""ETag / If-Match helpers (C4.1).

Convention:

* ETag value is ``"v{version}"`` (quoted per RFC 7232) where ``version``
  is the integer optimistic-locking counter on the aggregate.
* GET endpoints add ``ETag: "v{version}"`` to the response.
* Mutating endpoints accept an optional ``If-Match: "v{version}"``
  header. When present and the value mismatches the live aggregate
  version, the handler raises :class:`PreconditionFailedError` (HTTP 412).
* When ``If-Match`` is absent we keep the legacy behaviour — handler
  may still enforce optimistic locking via the request body's
  ``version`` field. This keeps backward compatibility through M+1.

Why a sentinel header parser:

Frontend sends quoted ETag values (``If-Match: "v5"``); FastAPI passes
them as raw strings. We strip the quotes + ``v`` prefix and validate
the int once, in one place, instead of duplicating the regex across
six entity routers.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import Header, Response

_ETAG_RE = re.compile(r'^"?v(\d+)"?$')


def parse_if_match(
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> int | None:
    """Parse ``If-Match: "v{N}"`` into the expected version.

    Returns ``None`` when the header is absent — handlers fall back
    to legacy optimistic-locking via the request body's ``version``
    field. Returns ``None`` on malformed values too (the handler
    still gets a "no precondition" signal — better UX than rejecting
    the whole request because of a stray quote).

    Args:
        if_match: Raw header value as injected by FastAPI.

    Returns:
        The integer version requested in ``If-Match``, or ``None``
        when the header is absent or malformed.
    """
    if if_match is None:
        return None
    match = _ETAG_RE.match(if_match.strip())
    if match is None:
        return None
    return int(match.group(1))


IfMatchVersion = Annotated[int | None, "Parsed If-Match version (None when absent)"]
"""Type alias used in route signatures.

Usage::

    @router.patch(...)
    async def update_product(
        product_id: uuid.UUID,
        body: ProductUpdateRequest,
        expected_version: int | None = Depends(parse_if_match),
        ...
    ):
        ...
"""


def attach_etag(response: Response, version: int) -> None:
    """Set ``ETag: "v{version}"`` on the response.

    Frontend stores this on the read and echoes it back as
    ``If-Match`` on the next mutate. Strong validator (no ``W/`` prefix)
    because the version field is a strict equality check, not a hash
    of the body — two responses with the same version always represent
    the exact same persisted state.
    """
    response.headers["ETag"] = f'"v{version}"'


__all__ = [
    "IfMatchVersion",
    "attach_etag",
    "parse_if_match",
]
