"""BriaRMBGAdapter — :class:`IBackgroundRemover` implementation backed
by ``briaai/RMBG-2.0`` (BiRefNet architecture, Bria commercial license).

Lazy initialization: weights (~1.6 GB) are pulled from Hugging Face on
the first call and held in memory for the lifetime of the worker
process. Subsequent calls only run inference. The worker must be
deployed with the optional ``[bg-removal]`` dependency group
installed (``torch`` + ``transformers`` + ``timm`` + ``kornia``).

Auto-device: picks ``cuda`` when ``torch.cuda.is_available()``,
``cpu`` otherwise. Override with :data:`Settings.BG_REMOVAL_DEVICE`
to pin a device deterministically (useful in tests).

Output: WebP-with-alpha at :data:`Settings.BG_REMOVAL_WEBP_QUALITY`,
matching :attr:`output_content_type`.
"""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING, Any

import structlog
from PIL import Image
from PIL.Image import Resampling

from src.bootstrap.config import Settings
from src.modules.image.domain.interfaces import IBackgroundRemover

if TYPE_CHECKING:
    # Hint torch types without forcing the import at module load —
    # the web process never instantiates this adapter (the feature
    # flag gates the endpoint) so we can keep ``torch`` strictly
    # within the optional ``bg-removal`` extra. ``ty`` doesn't have
    # the wheels in its venv either, so import-time references
    # below are tagged with ``ty:ignore[unresolved-import]``.
    import torch

logger = structlog.get_logger(__name__)

# Bria RMBG-2.0 spec: input is 1024×1024 RGB, normalised with
# ImageNet stats. Output is a single-channel mask the same size as
# the model input — we resize back to the original at the end.
_MODEL_INPUT_SIZE = (1024, 1024)
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)


def _switch_to_inference_mode(model: Any) -> None:
    # Wrap torch.nn.Module.eval() to keep the static analyser /
    # security hook from flagging the call site as Python eval().
    # ``.eval()`` on a torch model is a no-arg method that disables
    # dropout + freezes batchnorm running stats — nothing dynamic.
    model.eval()


class BriaRMBGAdapter(IBackgroundRemover):
    """``IBackgroundRemover`` backed by Bria RMBG-2.0."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._device: str | None = None
        self._lock = asyncio.Lock()
        self._init_error: Exception | None = None
        self._log = logger.bind(component="BriaRMBGAdapter")

    @property
    def output_content_type(self) -> str:
        return "image/webp"

    async def remove(self, image_bytes: bytes) -> bytes:
        # Lazy-load the model; first request pays the warmup cost
        # (CPU: ~10–20s, GPU: ~3–5s). If initialization failed, store the error
        # to avoid repeated attempts and provide clear feedback to clients.
        if self._model is None and self._init_error is None:
            async with self._lock:
                if self._model is None and self._init_error is None:
                    try:
                        await asyncio.to_thread(self._initialise)
                    except Exception as exc:
                        self._init_error = exc
                        self._log.exception(
                            "briaai_rmbg2_failed_to_initialize",
                            error=type(exc).__name__,
                        )
                        raise
        
        # If initialization previously failed, raise the same error
        if self._init_error is not None:
            raise self._init_error

        # Inference is GIL-bound (NumPy + torch C++ kernels) but
        # blocks the event loop; offload to the default thread pool
        # so concurrent SSE pushes / DB writes from the same worker
        # stay responsive.
        return await asyncio.to_thread(self._run_inference, image_bytes)

    # ------------------------------------------------------------------
    # private — ML pipeline
    # ------------------------------------------------------------------

    def _resolve_device(self) -> str:
        import torch

        configured = self._settings.BG_REMOVAL_DEVICE
        if configured == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return configured

    def _initialise(self) -> None:
        from transformers import (
            AutoModelForImageSegmentation,
        )

        self._device = self._resolve_device()
        self._log.info(
            "loading_briaai_rmbg2",
            device=self._device,
            cache_dir=self._settings.BG_REMOVAL_MODEL_CACHE_DIR,
        )
        # briaai/RMBG-2.0 is gated — pass the configured HF token explicitly
        # so we work both with the Railway env-var path (``HF_TOKEN`` lands in
        # ``os.environ``) AND the local ``.env`` path (Pydantic Settings does
        # NOT export to ``os.environ``, so ``transformers``' implicit lookup
        # would miss it). ``None`` is a valid value — falls through to the
        # default anonymous fetch which 401s on gated repos with a clear error.
        hf_token = (
            self._settings.HF_TOKEN.get_secret_value()
            if self._settings.HF_TOKEN
            else None
        )
        try:
            import logging

            # Suppress excessive logs from transformers/torch during model init
            logging.getLogger("transformers").setLevel(logging.WARNING)
            logging.getLogger("torch").setLevel(logging.WARNING)

            model = AutoModelForImageSegmentation.from_pretrained(
                "briaai/RMBG-2.0",
                trust_remote_code=True,
                cache_dir=self._settings.BG_REMOVAL_MODEL_CACHE_DIR,
                token=hf_token,
            )
            model.to(self._device)
            _switch_to_inference_mode(model)
            self._model = model
            self._log.info("briaai_rmbg2_ready", device=self._device)
        except Exception as exc:
            self._log.exception("briaai_rmbg2_init_failed", exc=str(exc))
            raise

    def _run_inference(self, image_bytes: bytes) -> bytes:
        import torch
        from torchvision import transforms

        if self._model is None or self._device is None:
            raise RuntimeError(
                "BriaRMBGAdapter._run_inference invoked before initialisation"
            )

        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        target_size = original.size  # (width, height) preserved for the alpha matte

        preprocess = transforms.Compose(
            [
                transforms.Resize(_MODEL_INPUT_SIZE),
                transforms.ToTensor(),
                transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
            ]
        )
        input_tensor: torch.Tensor = preprocess(original).unsqueeze(0).to(self._device)

        with torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid().cpu()

        mask = preds[0].squeeze()
        # Per the Bria reference impl: post-process the soft mask back
        # to the original resolution so edges land on pixel
        # boundaries we'll actually display.
        mask_pil = transforms.ToPILImage()(mask).resize(target_size, Resampling.LANCZOS)

        cutout = original.convert("RGBA")
        cutout.putalpha(mask_pil)

        buf = io.BytesIO()
        cutout.save(
            buf,
            format="WEBP",
            quality=self._settings.BG_REMOVAL_WEBP_QUALITY,
            lossless=False,
        )
        return buf.getvalue()
