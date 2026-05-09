"""``NoopBackgroundRemover`` — fallback :class:`IBackgroundRemover`.

Used by the web service (``BG_REMOVAL_ENABLED=False``) and unit tests
that exercise the dispatch / repository wiring without paying the
~1.6 GB model download cost.

Returns the input image unchanged (still framed as RGBA-WebP so the
contract stays honest). Production deployments wire
:class:`BriaRMBGAdapter` instead via the ``BG_REMOVAL_ENABLED`` flag
in the Dishka provider.
"""

from __future__ import annotations

import io

from PIL import Image

from src.modules.image.domain.interfaces import IBackgroundRemover


class NoopBackgroundRemover(IBackgroundRemover):
    """Identity adapter for environments without the ML stack."""

    @property
    def output_content_type(self) -> str:
        return "image/webp"

    async def remove(self, image_bytes: bytes) -> bytes:
        # Re-encode as RGBA-WebP so downstream consumers can rely
        # on a uniform shape even when the cutout is a no-op. Tests
        # that need to assert "model was actually invoked" should
        # use a mock instead of this adapter.
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=92, lossless=False)
        return buf.getvalue()
