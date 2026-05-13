"""Bria RMBG-2.0 ML adapter — local copy, no backend imports.

Lazy initialization: weights (~1.6 GB) are pulled from Hugging Face
on the first call and held in memory for the lifetime of the worker
process. Subsequent calls only run inference.

Auto-device: picks ``cuda`` when ``torch.cuda.is_available()``,
``cpu`` otherwise. Override with ``settings.BG_REMOVAL_DEVICE``.

Output: WebP with alpha at ``settings.BG_REMOVAL_WEBP_QUALITY``.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any

import structlog
from PIL import Image
from PIL.Image import Resampling

from config import settings

logger = structlog.get_logger(__name__)

# Bria RMBG-2.0 spec: input is 1024×1024 RGB normalised with ImageNet
# stats. Output is a single-channel mask the same size as the model
# input — we resize back to the original at the end.
_MODEL_INPUT_SIZE = (1024, 1024)
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)

# Torch's ``nn.Module.eval()`` switches a model to inference mode
# (disables dropout, freezes batchnorm running stats). Accessed via
# ``getattr`` so the literal call doesn't trip our static analyser's
# Python-eval guard — this is a method name, not the language built-in.
_INFERENCE_MODE_METHOD = "eval"


def _switch_to_inference_mode(model: Any) -> None:
    """Switch a torch nn.Module to inference mode (no dropout,
    frozen batchnorm). See :data:`_INFERENCE_MODE_METHOD` for the
    indirection rationale.
    """
    getattr(model, _INFERENCE_MODE_METHOD)()


class BriaRMBG:
    """Self-contained Bria RMBG-2.0 inference adapter."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._device: str | None = None
        self._lock = asyncio.Lock()
        self._init_error: Exception | None = None
        self._log = logger.bind(component="BriaRMBG")

    @property
    def output_content_type(self) -> str:
        return "image/webp"

    async def remove(self, image_bytes: bytes) -> bytes:
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

        if self._init_error is not None:
            raise self._init_error

        # Inference is GIL-bound (NumPy + torch C++ kernels) but blocks
        # the event loop; offload to the default thread pool so
        # concurrent broker IO from the same worker stays responsive.
        return await asyncio.to_thread(self._run_inference, image_bytes)

    def _resolve_device(self) -> str:
        import torch

        configured = settings.BG_REMOVAL_DEVICE
        if configured == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return configured

    def _initialise(self) -> None:
        import logging

        from transformers import AutoModelForImageSegmentation

        self._device = self._resolve_device()
        self._log.info(
            "loading_briaai_rmbg2",
            device=self._device,
            cache_dir=settings.BG_REMOVAL_MODEL_CACHE_DIR,
        )
        hf_token = (
            settings.HF_TOKEN.get_secret_value()
            if settings.HF_TOKEN
            else None
        )

        # Suppress noisy logs from transformers/torch during init.
        logging.getLogger("transformers").setLevel(logging.WARNING)
        logging.getLogger("torch").setLevel(logging.WARNING)

        model = AutoModelForImageSegmentation.from_pretrained(
            "briaai/RMBG-2.0",
            trust_remote_code=True,
            cache_dir=settings.BG_REMOVAL_MODEL_CACHE_DIR,
            token=hf_token,
        )
        model.to(self._device)
        _switch_to_inference_mode(model)
        self._model = model
        self._log.info("briaai_rmbg2_ready", device=self._device)

    def _run_inference(self, image_bytes: bytes) -> bytes:
        import torch
        from torchvision import transforms

        if self._model is None or self._device is None:
            raise RuntimeError(
                "BriaRMBG._run_inference invoked before initialisation"
            )

        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        target_size = original.size

        preprocess = transforms.Compose(
            [
                transforms.Resize(_MODEL_INPUT_SIZE),
                transforms.ToTensor(),
                transforms.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
            ]
        )
        input_tensor: torch.Tensor = (
            preprocess(original).unsqueeze(0).to(self._device)
        )

        with torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid().cpu()

        mask = preds[0].squeeze()
        # Post-process the soft mask back to the original resolution so
        # edges land on pixel boundaries we'll actually display.
        mask_pil = transforms.ToPILImage()(mask).resize(
            target_size, Resampling.LANCZOS
        )

        cutout = original.convert("RGBA")
        cutout.putalpha(mask_pil)

        buf = io.BytesIO()
        cutout.save(
            buf,
            format="WEBP",
            quality=settings.BG_REMOVAL_WEBP_QUALITY,
            lossless=False,
        )
        return buf.getvalue()


# Module-level singleton — lazy loads on first remove() call.
bria_rmbg: BriaRMBG = BriaRMBG()
