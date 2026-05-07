"""Input validators for the image module HTTP layer.

Ported from image_backend's shared validators module. Adapted to use
main backend's :class:`ValidationError` (HTTP 400) instead of the
former ``BadRequestError`` (which doesn't exist here).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from src.shared.exceptions import ValidationError

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
