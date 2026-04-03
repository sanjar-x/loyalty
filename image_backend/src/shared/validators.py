"""Shared input validators."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from src.shared.exceptions import BadRequestError

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
    """Raise BadRequestError if *content_type* is not an allowed image MIME type."""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise BadRequestError(
            message=f"Unsupported content type '{content_type}'.",
            error_code="INVALID_CONTENT_TYPE",
            details={
                "content_type": content_type,
                "allowed": sorted(ALLOWED_IMAGE_TYPES),
            },
        )


def validate_external_url(url: str) -> None:
    """Raise BadRequestError if *url* points to a private/internal network.

    Blocks:
    - Private/loopback/link-local IP ranges
    - Cloud metadata endpoints (169.254.169.254)
    - localhost and known internal hostnames
    - Non-http(s) schemes
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise BadRequestError(
            message=f"URL scheme '{parsed.scheme}' is not allowed. Use http or https.",
            error_code="INVALID_URL_SCHEME",
            details={"url": url},
        )

    hostname = parsed.hostname
    if not hostname:
        raise BadRequestError(
            message="URL has no hostname.",
            error_code="INVALID_URL",
            details={"url": url},
        )

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise BadRequestError(
            message=f"Hostname '{hostname}' is not allowed.",
            error_code="BLOCKED_HOSTNAME",
            details={"hostname": hostname},
        )

    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise BadRequestError(
            message=f"Cannot resolve hostname '{hostname}'.",
            error_code="UNRESOLVABLE_HOSTNAME",
            details={"hostname": hostname},
        ) from e

    for _, _, _, _, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise BadRequestError(
                message="External URLs must point to public hosts.",
                error_code="PRIVATE_URL",
                details={"resolved_ip": str(ip)},
            )
