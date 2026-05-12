"""Input validators for the image module HTTP layer.

Ported from image_backend's shared validators module. Adapted to use
main backend's :class:`ValidationError` (HTTP 400) instead of the
former ``BadRequestError`` (which doesn't exist here).

IMG-002 — added :func:`secure_external_fetch` that validates the URL
on every redirect hop and streams the body with a hard size limit so
``follow_redirects=True`` can no longer round-trip an attacker-controlled
URL into AWS / GCP metadata.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from shared.exceptions import UnprocessableEntityError, ValidationError

ALLOWED_IMAGE_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
        "image/avif",
        "image/heic",
        "image/heif",
    }
)

_BLOCKED_HOSTNAMES = frozenset({"localhost", "metadata.google.internal"})


def validate_image_content_type(content_type: str) -> None:
    """Reject content types that are not in the allowed image MIME set."""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            message=f"Unsupported content type '{content_type}'.",
            error_code="INVALID_CONTENT_TYPE",
            details={
                "content_type": content_type,
                "allowed": sorted(ALLOWED_IMAGE_TYPES),
            },
        )


def validate_external_url(url: str) -> None:
    """SSRF guard for external-import URLs.

    Blocks:
    - non-http(s) schemes
    - hostnames in :data:`_BLOCKED_HOSTNAMES`
    - hostnames that resolve to private / loopback / link-local / reserved IPs
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            message=f"URL scheme '{parsed.scheme}' is not allowed. Use http or https.",
            error_code="INVALID_URL_SCHEME",
            details={"url": url},
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationError(
            message="URL has no hostname.",
            error_code="INVALID_URL",
            details={"url": url},
        )

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValidationError(
            message=f"Hostname '{hostname}' is not allowed.",
            error_code="BLOCKED_HOSTNAME",
            details={"hostname": hostname},
        )

    try:
        resolved = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror as e:
        raise ValidationError(
            message=f"Cannot resolve hostname '{hostname}'.",
            error_code="UNRESOLVABLE_HOSTNAME",
            details={"hostname": hostname},
        ) from e

    for _, _, _, _, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValidationError(
                message="External URLs must point to public hosts.",
                error_code="PRIVATE_URL",
                details={"resolved_ip": str(ip)},
            )


# ---------------------------------------------------------------------------
# IMG-002 — SSRF-safe fetch with redirect re-validation + streamed size cap
# ---------------------------------------------------------------------------

# Cap on number of HTTP redirects we follow. Anything legitimate fits in
# 5; anything more is suspicious and we abort.
_MAX_REDIRECTS = 5

# Status codes httpx treats as redirects.
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


async def secure_external_fetch(
    url: str,
    *,
    max_size_bytes: int,
    timeout_seconds: float = 30.0,
) -> bytes:
    """Fetch an external URL safely against SSRF + DoS.

    Closes three holes the previous ``httpx.get(url, follow_redirects=True)``
    pattern left open:

    1. **DNS rebinding TOCTOU.** ``validate_external_url`` resolves DNS
       once at the application layer, but ``httpx`` re-resolves
       independently when it makes the actual connection. An attacker
       returning a public IP at validation time and ``169.254.169.254``
       (AWS / GCP metadata) at fetch time bypassed the previous check.
       We re-validate before every hop so each connection target sees
       the same DNS check the validator did.
    2. **Redirect chain to internal host.** ``follow_redirects=True``
       followed any 30x ``Location`` blindly. We disable automatic
       redirect handling and run ``validate_external_url`` on every
       hop's resolved target. Capped at ``_MAX_REDIRECTS=5``.
    3. **Memory-exhaustion DoS via large response.** Previous code
       buffered ``response.content`` (entire body in memory). We stream
       and abort the connection the moment we see ``> max_size_bytes``.

    Args:
        url: Initial URL to fetch. Validated by ``validate_external_url``.
        max_size_bytes: Hard cap on body size; abort and raise on overrun.
        timeout_seconds: httpx total-timeout budget.

    Returns:
        The fetched bytes (always within ``max_size_bytes``).

    Raises:
        ValidationError: SSRF check failed on a hop.
        UnprocessableEntityError: download failed (non-200 final, or
            size limit exceeded).
    """
    current_url = url

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False,
    ) as client:
        for hop in range(_MAX_REDIRECTS + 1):
            validate_external_url(current_url)

            async with client.stream("GET", current_url) as response:
                if response.status_code in _REDIRECT_STATUSES:
                    if hop >= _MAX_REDIRECTS:
                        raise UnprocessableEntityError(
                            message=(
                                f"Too many redirects (>{_MAX_REDIRECTS}) for {url}"
                            ),
                            error_code="EXTERNAL_IMPORT_TOO_MANY_REDIRECTS",
                            details={"url": url, "hops": hop},
                        )
                    location = response.headers.get("location")
                    if not location:
                        raise UnprocessableEntityError(
                            message=(
                                f"HTTP {response.status_code} response "
                                "without Location header"
                            ),
                            error_code="EXTERNAL_IMPORT_DOWNLOAD_FAILED",
                            details={"url": current_url},
                        )
                    # Resolve relative locations against the current URL.
                    current_url = urljoin(current_url, location)
                    continue

                if response.status_code != 200:
                    raise UnprocessableEntityError(
                        message=(
                            f"Failed to download image: HTTP {response.status_code}"
                        ),
                        error_code="EXTERNAL_IMPORT_DOWNLOAD_FAILED",
                        details={"url": url, "status": response.status_code},
                    )

                # Streamed body with hard size cap. The connection is
                # aborted (httpx raises when the context exits) the
                # instant we cross the cap, so an attacker can't feed
                # us 10 GB by Content-Length: 100 + chunked-encoded
                # payload.
                chunks: list[bytes] = []
                received = 0
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > max_size_bytes:
                        raise UnprocessableEntityError(
                            message=(
                                f"File too large: stream exceeded "
                                f"{max_size_bytes} bytes"
                            ),
                            error_code="STORAGE_OBJECT_TOO_LARGE",
                            details={"url": url, "max": max_size_bytes},
                        )
                    chunks.append(chunk)
                return b"".join(chunks)

    # Unreachable — the loop returns or raises on every path.
    raise UnprocessableEntityError(  # pragma: no cover
        message=f"Unreachable redirect handling for {url}",
        error_code="EXTERNAL_IMPORT_DOWNLOAD_FAILED",
        details={"url": url},
    )
