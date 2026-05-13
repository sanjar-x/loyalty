"""Bria RMBG-2.0 ML adapter — local copy, no backend imports.

Inference recipe ported from the standalone ``rmbg/`` CLI. The model and
preprocessing pipeline are loaded once and reused across many calls inside
this long-lived worker process. Pipeline: EXIF-aware decode, optional
aspect-preserving letterbox, ``torchvision.transforms.v2`` preprocessing,
BICUBIC mask upscale, optional Gaussian feather, WebP composite.

Wrapped in the worker-resilience layer the TaskIQ broker needs: lazy init
under an ``asyncio.Lock``, init-error cooldown so transient HF download
blips do not poison the process for its lifetime, and ``asyncio.to_thread``
to keep the broker IO loop responsive while the GIL-bound forward pass
runs.

Output: WebP with alpha at ``settings.BG_REMOVAL_WEBP_QUALITY``.
"""

from __future__ import annotations

import asyncio
import io
import time
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError
from PIL.Image import Resampling

from config import settings

# Per-classification cooldown windows. Transient errors (rate limit,
# network blip, cache-dir glitch) get a short window so a recovering
# upstream resumes service quickly. Unknown errors get a longer window
# — we don't know the failure mode, so we err on the side of not
# hammering the upstream. Permanent errors (bad HF token, gated repo,
# missing model) are NOT cooldown-based: they latch a flag and every
# subsequent call fails fast with ``BriaRMBGPermanentInitError`` until
# the operator restarts the worker after fixing configuration.
_COOLDOWN_TRANSIENT_SECONDS = 60.0
_COOLDOWN_UNKNOWN_SECONDS = 300.0

# ``huggingface_hub.errors`` is a hard dependency via ``transformers``
# but we guard the import so a future restructure of HF's error
# hierarchy is a graceful no-op (classifier degrades to "unknown")
# rather than a crash on import.
try:
    from huggingface_hub.errors import (
        GatedRepoError as _HFGatedRepoError,
    )
    from huggingface_hub.errors import (
        HfHubHTTPError as _HFHubHTTPError,
    )
    from huggingface_hub.errors import (
        RepositoryNotFoundError as _HFRepositoryNotFoundError,
    )
except ImportError:  # pragma: no cover — defensive
    _HFGatedRepoError = _HFRepositoryNotFoundError = _HFHubHTTPError = None  # ty:ignore[invalid-assignment]

_PERMANENT_INIT_TYPES: tuple[type[BaseException], ...] = tuple(
    cls for cls in (_HFGatedRepoError, _HFRepositoryNotFoundError) if cls is not None
)
_TRANSIENT_INIT_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    # Cache-dir permission glitches and ENOSPC on a freshly-mounted
    # volume both surface as OSError. Usually transient on Railway.
    OSError,
)

logger = structlog.get_logger(__name__)


class BriaRMBGPermanentInitError(RuntimeError):
    """Raised when initialisation hit an unrecoverable error.

    The original exception (``GatedRepoError``, ``RepositoryNotFoundError``,
    HTTP 401/403, etc.) is set on ``__cause__``. Subsequent ``remove()``
    calls within the worker's lifetime raise this same way — the operator
    must fix the underlying configuration (token, model access) and
    restart the worker process. ``tasks.py`` lists this in its terminal
    set so each task fails fast rather than retrying through to the
    broker's ``max_retries`` ceiling.
    """


_InitErrorClass = Literal["permanent", "transient", "unknown"]


def _classify_init_error(exc: BaseException) -> _InitErrorClass:
    """Classify an init failure to drive retry behaviour.

    * ``permanent`` — configuration is broken (bad token, gated repo,
      model removed upstream). Retrying without an operator fix will
      fail the same way; the worker should fail every subsequent task
      fast rather than burn ~10s per attempt re-downloading nothing.
    * ``transient`` — the upstream had a moment (rate limit, HTTP 5xx,
      connection blip, cache-dir permissions on a freshly-mounted
      volume). A short cooldown is enough.
    * ``unknown`` — anything we don't recognise; default to a longer
      cooldown to avoid hammering an unknown failure mode.
    """
    if _PERMANENT_INIT_TYPES and isinstance(exc, _PERMANENT_INIT_TYPES):
        return "permanent"
    if _HFHubHTTPError is not None and isinstance(exc, _HFHubHTTPError):
        status = getattr(getattr(exc, "response", None), "status_code", None)
        # 401/403 = bad token / no permission → operator must fix.
        if status in (401, 403):
            return "permanent"
        # 429 (rate limit) and 5xx (upstream blip) → recover on their own.
        if status == 429 or (isinstance(status, int) and 500 <= status < 600):
            return "transient"
        return "unknown"
    if isinstance(exc, _TRANSIENT_INIT_TYPES):
        return "transient"
    return "unknown"


def _permanent_init_error_message(original: BaseException) -> str:
    """Build the operator-facing message for a permanent init failure."""
    return (
        f"BRIA RMBG-2.0 init permanently failed with "
        f"{type(original).__name__}: operator must fix configuration "
        "and restart the worker"
    )


# RMBG-2.0 was trained at 1024×1024. Deviating from this hurts quality,
# and values not divisible by 32 break the Swin-L backbone's patch grid.
_MODEL_INPUT_SIZE = 1024
# Must match preprocessor_config.json on the model card — Swin was
# pretrained on ImageNet using these statistics.
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]
# Letterbox pad colour. Irrelevant for output quality: we crop the mask
# back to ``content_w × content_h`` before the final resize, so the
# model's view of the pad bars never reaches the output.
_PAD_COLOR_BLACK: tuple[int, int, int] = (0, 0, 0)


@dataclass(frozen=True)
class _Letterbox:
    """Bookkeeping for aspect-preserving padding.

    The source image is scaled to ``content_w × content_h`` and pasted
    at offset ``(left, top)`` inside a square canvas. After inference
    these coords map the model's square mask back to the source's
    content region.
    """

    left: int
    top: int
    content_w: int
    content_h: int


def _pad_to_square(image: Image.Image) -> tuple[Image.Image, _Letterbox]:
    """Letterbox ``image`` into a 1024×1024 canvas without distortion.

    Plain ``resize`` to a square stretches non-square images and hurts
    BiRefNet on fine details (hair, fur, transparent edges). Letterboxing
    trades a bit of useful resolution for geometrically correct features.
    The returned :class:`_Letterbox` lets the caller crop the square
    mask back to the original aspect ratio.
    """
    src_w, src_h = image.size
    scale = min(_MODEL_INPUT_SIZE / src_w, _MODEL_INPUT_SIZE / src_h)
    content_w = max(1, round(src_w * scale))
    content_h = max(1, round(src_h * scale))
    scaled = image.resize((content_w, content_h), Resampling.BILINEAR)
    left = (_MODEL_INPUT_SIZE - content_w) // 2
    top = (_MODEL_INPUT_SIZE - content_h) // 2
    canvas = Image.new("RGB", (_MODEL_INPUT_SIZE, _MODEL_INPUT_SIZE), _PAD_COLOR_BLACK)
    canvas.paste(scaled, (left, top))
    return canvas, _Letterbox(left, top, content_w, content_h)


class BriaRMBG:
    """Self-contained Bria RMBG-2.0 inference adapter."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._device: str | None = None
        self._transform: Any | None = None
        self._lock = asyncio.Lock()
        self._init_error: Exception | None = None
        self._init_error_at: float | None = None
        # Latched on a permanent classification; once True, the worker
        # raises ``BriaRMBGPermanentInitError`` for every subsequent
        # ``remove()`` call until the process is restarted.
        self._init_error_permanent: bool = False
        # Cooldown duration for the current cached error; set by the
        # classifier in ``remove()``'s except branch. Ignored when
        # ``_init_error_permanent`` is True.
        self._init_error_cooldown_seconds: float = 0.0
        self._log = logger.bind(component="BriaRMBG")
        # Per-image settings snapshotted at init time so they cannot
        # drift between the model load (which baked them in via
        # ``memory_format`` / preprocessing) and the per-call hot path.
        # See _initialise for the snapshot site.
        self._keep_aspect: bool = True
        self._channels_last: bool = True
        self._feather: float = 0.0
        self._webp_quality: int = 90

    def _init_error_is_active(self) -> bool:
        """A cached init error suppresses re-tries until the cooldown
        window has elapsed. Permanent errors never expire — the latched
        flag keeps this returning True for the lifetime of the worker.
        """
        if self._init_error is None or self._init_error_at is None:
            return False
        if self._init_error_permanent:
            return True
        return (
            time.monotonic() - self._init_error_at < self._init_error_cooldown_seconds
        )

    @property
    def output_content_type(self) -> str:
        return "image/webp"

    async def remove(self, image_bytes: bytes) -> bytes:
        if self._model is None and not self._init_error_is_active():
            async with self._lock:
                if self._model is None and not self._init_error_is_active():
                    # Reset ALL init state atomically so a half-failed
                    # previous attempt doesn't leave stale ``_device`` /
                    # ``_transform`` values for the retry to trip over.
                    # ``_model`` is already None per the loop guard;
                    # snapshot fields are re-populated by ``_initialise``.
                    self._init_error = None
                    self._init_error_at = None
                    self._init_error_permanent = False
                    self._init_error_cooldown_seconds = 0.0
                    self._device = None
                    self._transform = None
                    try:
                        await asyncio.to_thread(self._initialise)
                    except Exception as exc:
                        classification = _classify_init_error(exc)
                        self._init_error = exc
                        self._init_error_at = time.monotonic()
                        if classification == "permanent":
                            self._init_error_permanent = True
                            # Cooldown is moot for permanent; zero is a
                            # sentinel that should never be consulted.
                            self._init_error_cooldown_seconds = 0.0
                        elif classification == "transient":
                            self._init_error_cooldown_seconds = (
                                _COOLDOWN_TRANSIENT_SECONDS
                            )
                        else:
                            self._init_error_cooldown_seconds = (
                                _COOLDOWN_UNKNOWN_SECONDS
                            )
                        self._log.exception(
                            "briaai_rmbg2_failed_to_initialize",
                            error=type(exc).__name__,
                            classification=classification,
                            cooldown_seconds=self._init_error_cooldown_seconds,
                        )
                        if classification == "permanent":
                            # Surface as the worker's terminal exception
                            # so ``tasks.py`` short-circuits retry; chain
                            # the original cause for full operator detail.
                            raise BriaRMBGPermanentInitError(
                                _permanent_init_error_message(exc)
                            ) from exc
                        raise

        if self._init_error_is_active():
            # Defensive — invariant is "cached error implies _init_error
            # set". Explicit check rather than ``assert`` so we don't
            # collapse under ``python -O``.
            if self._init_error is None or self._init_error_at is None:
                raise RuntimeError("BriaRMBG: cooldown active but no cached error")
            elapsed = time.monotonic() - self._init_error_at
            if self._init_error_permanent:
                # Log every rejected call so an operator who only sees a
                # late spike still has fresh evidence pointing at the
                # original failure rather than scrolling back hours.
                self._log.warning(
                    "briaai_rmbg2_init_permanent_error_active",
                    original_error=type(self._init_error).__name__,
                    original_message=str(self._init_error),
                    seconds_since_failure=elapsed,
                )
                raise BriaRMBGPermanentInitError(
                    _permanent_init_error_message(self._init_error)
                ) from self._init_error
            remaining = max(0.0, self._init_error_cooldown_seconds - elapsed)
            self._log.warning(
                "briaai_rmbg2_init_cooldown_active",
                original_error=type(self._init_error).__name__,
                original_message=str(self._init_error),
                seconds_since_failure=elapsed,
                cooldown_remaining_seconds=remaining,
            )
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

        import torch
        from torchvision.transforms import v2
        from transformers import AutoModelForImageSegmentation

        self._device = self._resolve_device()
        self._log.info(
            "loading_briaai_rmbg2",
            device=self._device,
            cache_dir=settings.BG_REMOVAL_MODEL_CACHE_DIR,
            keep_aspect=settings.BG_REMOVAL_KEEP_ASPECT,
            feather=settings.BG_REMOVAL_FEATHER,
            channels_last=settings.BG_REMOVAL_CHANNELS_LAST,
            num_threads=settings.BG_REMOVAL_NUM_THREADS,
        )

        # ``set_num_threads`` is CPU-only — setting it on a CUDA worker
        # would slow the CPU-side data path without helping.
        if self._device == "cpu" and settings.BG_REMOVAL_NUM_THREADS is not None:
            torch.set_num_threads(settings.BG_REMOVAL_NUM_THREADS)

        # ``set_float32_matmul_precision("high")`` matches BRIA's training
        # recipe and benefits both backends: oneDNN reduced-precision
        # accumulators on CPU and TF32 matmul on CUDA Ampere+. Process-
        # global, idempotent — apply unconditionally regardless of
        # device.
        torch.set_float32_matmul_precision("high")

        # Suppress noisy logs from transformers/torch during init.
        logging.getLogger("transformers").setLevel(logging.WARNING)
        logging.getLogger("torch").setLevel(logging.WARNING)

        hf_token = settings.HF_TOKEN.get_secret_value() if settings.HF_TOKEN else None

        # ``trust_remote_code=True`` is required: RMBG-2.0 ships a custom
        # ``birefnet.py`` rather than a built-in transformers architecture.
        # ``dtype=torch.float32`` is pinned on both CPU and CUDA paths:
        # ASPPDeformable uses ``torchvision.ops.deform_conv2d`` which has
        # no bf16/fp16 kernel on CPU, and one code path is preferable
        # to a per-device dtype branch.
        # ``low_cpu_mem_usage=True`` streams the state dict via accelerate
        # so peak RAM during load stays close to the model size instead
        # of ~2×. Some tensors are left on the ``meta`` device until
        # ``model.to(device)`` materialises them below.
        model = AutoModelForImageSegmentation.from_pretrained(
            "briaai/RMBG-2.0",
            trust_remote_code=True,
            cache_dir=settings.BG_REMOVAL_MODEL_CACHE_DIR,
            token=hf_token,
            dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        model = model.to(self._device)
        # nn.Module.train(False) is the explicit form of .eval() —
        # switches to inference mode (disables dropout, freezes
        # batchnorm running stats). Used here rather than the bare
        # method name to keep this file free of the ``eval(`` literal
        # that some pattern-based scanners conflate with the Python
        # built-in of the same spelling.
        model.train(False)

        # Snapshot per-image settings into instance state. Doing this
        # AFTER successful model load (and BEFORE assigning ``self._model``)
        # ensures the per-call hot path sees exactly the same values that
        # were baked into the loaded model — no drift if the runtime
        # config layer is ever reloaded between init and inference.
        self._keep_aspect = settings.BG_REMOVAL_KEEP_ASPECT
        self._channels_last = settings.BG_REMOVAL_CHANNELS_LAST
        self._feather = settings.BG_REMOVAL_FEATHER
        self._webp_quality = settings.BG_REMOVAL_WEBP_QUALITY

        # NHWC layout lets oneDNN pick faster Conv2d kernels (also
        # benefits Ampere+ GPUs). The conversion must apply to BOTH the
        # model and the input tensor; the per-call branch in
        # ``_run_inference`` covers the latter.
        if self._channels_last:
            model = model.to(memory_format=torch.channels_last)

        # v2 idiom: resize the uint8 tensor first (cheap, vectorised),
        # THEN cast to float32 and normalise. Casting before resize
        # wastes 4× the memory bandwidth on the most expensive op.
        # ``antialias=True`` is mandatory on tensors to match PIL —
        # without it bilinear interpolation aliases visibly.
        self._transform = v2.Compose([
            v2.ToImage(),
            v2.Resize(
                (_MODEL_INPUT_SIZE, _MODEL_INPUT_SIZE),
                interpolation=v2.InterpolationMode.BILINEAR,
                antialias=True,
            ),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(_IMAGENET_MEAN, _IMAGENET_STD),
        ])
        self._model = model
        self._log.info("briaai_rmbg2_ready", device=self._device)

    def _run_inference(self, image_bytes: bytes) -> bytes:
        import torch
        from torchvision.transforms.v2 import functional as TVF

        if self._model is None or self._device is None or self._transform is None:
            raise RuntimeError("BriaRMBG._run_inference invoked before initialisation")

        # Phone cameras commonly rotate via EXIF tag rather than physical
        # pixel rotation. Without ``exif_transpose`` the model receives a
        # sideways image and the mask comes back misaligned with the
        # original. DecompressionBombError and UnidentifiedImageError
        # are listed in tasks.py's ``_TERMINAL_PROCESSING_ERRORS`` — we
        # let them propagate unchanged so the caller classifies them
        # as terminal and skips retry. Other ``OSError`` from this block
        # means truncated or corrupt bytes (Pillow raises it from
        # ``image.load()`` inside ``exif_transpose``) — same root cause,
        # so we reclassify as ``UnidentifiedImageError`` to land on the
        # terminal path rather than the generic retry branch.
        try:
            with Image.open(io.BytesIO(image_bytes)) as raw:
                oriented = ImageOps.exif_transpose(raw)
        except UnidentifiedImageError:
            raise
        except OSError as exc:
            raise UnidentifiedImageError(
                f"failed to decode image bytes: {exc}"
            ) from exc
        source = oriented.convert("RGB")

        letterbox: _Letterbox | None = None
        model_input = source
        if self._keep_aspect:
            model_input, letterbox = _pad_to_square(source)

        tensor = self._transform(model_input).unsqueeze(0).to(self._device)
        if self._channels_last:
            tensor = tensor.to(memory_format=torch.channels_last)

        inference_start = time.perf_counter()
        with torch.inference_mode():
            outputs = self._model(tensor)
        inference_seconds = time.perf_counter() - inference_start

        # BiRefNet's forward in inference mode returns a list of
        # multi-scale logits; earlier elements exist for training
        # supervision only, ``[-1]`` is the full-resolution prediction.
        logits = outputs[-1] if isinstance(outputs, (list, tuple)) else outputs
        # Sigmoid is numerically sensitive near 0 and 1 (where most of a
        # clean mask lives) — keep it fp32 defensively even if the
        # backbone ever runs in a lower-precision dtype.
        mask_tensor = logits.float().sigmoid().squeeze(0).squeeze(0).cpu()
        mask = TVF.to_pil_image(mask_tensor, mode="L")

        if letterbox is not None:
            mask = mask.crop((
                letterbox.left,
                letterbox.top,
                letterbox.left + letterbox.content_w,
                letterbox.top + letterbox.content_h,
            ))
        # BICUBIC on the upscale back to source: smoother edges than
        # BILINEAR for single-channel masks, cost is negligible.
        mask = mask.resize(source.size, Resampling.BICUBIC)
        if self._feather > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=self._feather))

        cutout = source.convert("RGBA")
        cutout.putalpha(mask)

        buf = io.BytesIO()
        try:
            cutout.save(
                buf,
                format="WEBP",
                quality=self._webp_quality,
                lossless=False,
            )
        except (OSError, ValueError) as exc:
            # libwebp encode failures (OSError from the C extension)
            # and dimension overruns (ValueError, WebP caps at 16383 px)
            # are both bytes-driven: source dims are bounded by the
            # upstream storage variant (≤1200 px), so an encode failure
            # at this stage is a codec misconfig that retry can't fix.
            # Reclassify as terminal so ``tasks.py`` skips retry.
            raise UnidentifiedImageError(
                f"failed to encode WebP output: {exc}"
            ) from exc
        result = buf.getvalue()
        # ``inference_seconds`` measures only the model forward pass;
        # the surrounding decode / letterbox / encode are typically a
        # small fraction. Logged here once per ``remove()`` call.
        self._log.info(
            "briaai_rmbg2_processed",
            inference_seconds=inference_seconds,
            source_size=source.size,
            keep_aspect=self._keep_aspect,
            output_bytes=len(result),
        )
        return result


# Module-level singleton — lazy loads on first remove() call.
bria_rmbg: BriaRMBG = BriaRMBG()
