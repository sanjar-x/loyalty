'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactCrop from 'react-image-crop';
import { fetchImageAsFile } from '@/entities/product';
import styles from './ImageViewer.module.css';

export default function ImageViewer({
  images,
  uploads = {},
  initialIndex = 0,
  // Bg-removal state lifted to <ImagesSection> via useBgRemoval — passed
  // in so the editor only renders the «Без фона / С фоном» toggle when a
  // derivation exists. The trigger itself lives on the gallery thumbnail
  // so the user can fire it without opening this modal.
  bgRemovalStateByLocalId = {},
  bgVariantByLocalId = {},
  onToggleBgVariant,
  onClose,
  onReplace,
}) {
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const [cropping, setCropping] = useState(false);
  const [crop, setCrop] = useState(undefined);
  const [completedCrop, setCompletedCrop] = useState(null);
  const [applying, setApplying] = useState(false);
  const [aspect, setAspect] = useState(undefined);
  const [fetching, setFetching] = useState(false);
  const [cropError, setCropError] = useState(null);
  const imgRef = useRef(null);

  // Track blob: URLs we created locally so we can revoke them on unmount.
  // Without this every crop / fetch leaves a blob in memory until the tab
  // is closed.
  const ownedBlobUrlsRef = useRef(new Set());
  useEffect(() => {
    const owned = ownedBlobUrlsRef.current;
    return () => {
      for (const url of owned) URL.revokeObjectURL(url);
      owned.clear();
    };
  }, []);

  const current = images[activeIndex];
  const total = images.length;

  // The source image for cropping: always the original (before any crop)
  const cropSrc = current?.originalUrl || current?.url;

  // navigateTo is defined later in the component body; route through a ref so
  // the useCallback identities below stay stable. The ref is updated in an
  // effect (never during render) — see `useEffect` for navigateToRef below.
  const navigateToRef = useRef(null);

  const goPrev = useCallback(() => {
    const prev = activeIndex > 0 ? activeIndex - 1 : total - 1;
    navigateToRef.current?.(prev);
  }, [total, activeIndex]);

  const goNext = useCallback(() => {
    const next = activeIndex < total - 1 ? activeIndex + 1 : 0;
    navigateToRef.current?.(next);
  }, [total, activeIndex]);

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        if (cropping) {
          setCropping(false);
          setCrop(undefined);
          setCompletedCrop(null);
        } else {
          onClose();
        }
      }
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
    }
    const prevOverflow = document.body.style.overflow;
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose, goPrev, goNext, cropping]);

  useEffect(() => {
    if (activeIndex >= total) setActiveIndex(Math.max(0, total - 1));
  }, [total, activeIndex]);

  useEffect(() => {
    if (!images || images.length === 0) onClose();
  }, [images, onClose]);

  // Keep navigateToRef in sync with the latest navigateTo closure.
  // Updated in an effect so we never mutate refs during render.
  useEffect(() => {
    navigateToRef.current = navigateTo;
  });

  if (!current || total === 0) return null;

  const ASPECT_RATIOS = [
    { label: 'Свободно', value: undefined },
    { label: '1:1', value: 1 },
    { label: '4:5', value: 4 / 5 },
    { label: '3:4', value: 3 / 4 },
    { label: '16:9', value: 16 / 9 },
  ];

  async function handleStartCrop() {
    // For images without a local file — fetch via BFF proxy to avoid CORS
    if (!current.file) {
      const imageUrl = uploads[current.localId]?.url || current.url;
      setFetching(true);
      try {
        const file = await fetchImageAsFile(imageUrl);
        const blobUrl = URL.createObjectURL(file);
        ownedBlobUrlsRef.current.add(blobUrl);
        onReplace?.(current.localId, {
          ...current,
          file,
          originalUrl: blobUrl,
          originalFile: file,
          url: blobUrl,
        });
      } catch (err) {
        setCropError(
          err?.message || 'Не удалось загрузить изображение для кадрирования',
        );
        setFetching(false);
        return;
      }
      setFetching(false);
    }
    setAspect(undefined);
    setCrop(
      current.lastCrop || { unit: '%', x: 0, y: 0, width: 100, height: 100 },
    );
    setCompletedCrop(null);
    setCropping(true);
  }

  function handleCancelCrop() {
    setCropping(false);
    setCrop(undefined);
    setCompletedCrop(null);
    setAspect(undefined);
  }

  function handleAspectChange(newAspect) {
    setAspect(newAspect);
    if (newAspect && imgRef.current) {
      const { width, height } = imgRef.current;
      const newCrop = centerCropForAspect(width, height, newAspect);
      setCrop(newCrop);
      // Compute pixel crop so "Применить" stays enabled
      setCompletedCrop({
        x: (newCrop.x / 100) * width,
        y: (newCrop.y / 100) * height,
        width: (newCrop.width / 100) * width,
        height: (newCrop.height / 100) * height,
        unit: 'px',
      });
    }
  }

  function centerCropForAspect(imgW, imgH, ratio) {
    let cropW, cropH;
    if (imgW / imgH > ratio) {
      cropH = imgH;
      cropW = cropH * ratio;
    } else {
      cropW = imgW;
      cropH = cropW / ratio;
    }
    const pctW = (cropW / imgW) * 100;
    const pctH = (cropH / imgH) * 100;
    return {
      unit: '%',
      x: (100 - pctW) / 2,
      y: (100 - pctH) / 2,
      width: pctW,
      height: pctH,
    };
  }

  async function applyCrop(targetImage, cropData, completedCropData) {
    const image = imgRef.current;
    if (!image || !completedCropData?.width || !completedCropData?.height)
      return;

    const canvas = document.createElement('canvas');
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    canvas.width = completedCropData.width * scaleX;
    canvas.height = completedCropData.height * scaleY;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(
      image,
      completedCropData.x * scaleX,
      completedCropData.y * scaleY,
      completedCropData.width * scaleX,
      completedCropData.height * scaleY,
      0,
      0,
      canvas.width,
      canvas.height,
    );

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (b) => (b ? resolve(b) : reject(new Error('toBlob failed'))),
        'image/jpeg',
        0.92,
      );
    });

    const newUrl = URL.createObjectURL(blob);
    ownedBlobUrlsRef.current.add(newUrl);
    const newFile = new File([blob], targetImage.file?.name || 'cropped.jpg', {
      type: 'image/jpeg',
    });

    onReplace?.(targetImage.localId, {
      ...targetImage,
      file: newFile,
      url: newUrl,
      source: 'file',
      originalUrl: targetImage.originalUrl || targetImage.url,
      originalFile: targetImage.originalFile || targetImage.file,
      lastCrop: cropData,
    });
  }

  async function handleApplyCrop() {
    if (!completedCrop?.width) return;
    setApplying(true);
    try {
      await applyCrop(current, crop, completedCrop);
      resetCropState();
    } catch (err) {
      // Surface to UI rather than DevTools — crop failure leaves the user
      // with no apparent change after pressing «Применить», which is
      // confusing without explanation.
      setCropError(err?.message || 'Не удалось применить кадрирование');
    } finally {
      setApplying(false);
    }
  }

  function resetCropState() {
    setCropping(false);
    setCrop(undefined);
    setCompletedCrop(null);
    setAspect(undefined);
  }

  async function navigateTo(idx) {
    if (idx === activeIndex) return;
    const wasCropping = cropping;
    if (cropping && completedCrop?.width) {
      try {
        await applyCrop(current, crop, completedCrop);
      } catch (err) {
        setCropError(
          err?.message ||
            'Не удалось применить кадрирование при переключении изображения',
        );
      }
    }
    // Reset crop state but keep crop mode if we were cropping
    setCrop(undefined);
    setCompletedCrop(null);
    setAspect(undefined);
    setActiveIndex(idx);
    if (wasCropping) {
      // Re-enter crop mode for the new image on next render
      const nextImage = images[idx];
      if (nextImage && (nextImage.source === 'file' || nextImage.file)) {
        setCrop(
          nextImage.lastCrop || {
            unit: '%',
            x: 0,
            y: 0,
            width: 100,
            height: 100,
          },
        );
      } else {
        setCropping(false);
      }
    }
  }

  const canCrop = current.source === 'file' || current.source === 'url';

  // Bg-removal state lives in <ImagesSection> via useBgRemoval. Editor
  // only reads — no fetching, no SSE subscription, no spinner. Trigger
  // is on the gallery thumbnail.
  const bgRemovalState = bgRemovalStateByLocalId[current?.localId] ?? {
    status: 'idle',
  };
  const bgVariant = bgVariantByLocalId[current?.localId] ?? 'original';

  function handleToggleBgVariant() {
    if (!current || bgRemovalState.status !== 'completed') return;
    onToggleBgVariant?.(current.localId);
  }

  const previewUrl =
    bgVariant === 'no-background' && bgRemovalState.derivedUrl
      ? bgRemovalState.derivedUrl
      : uploads[current.localId]?.url || current.url;

  return (
    <div
      className={styles.overlay}
      onClick={cropping ? undefined : onClose}
      role="dialog"
      aria-label="Просмотр изображения"
    >
      <div className={styles.container} onClick={(e) => e.stopPropagation()}>
        <div className={styles.sidebar}>
          {images.map((img, idx) => (
            <button
              key={img.localId}
              type="button"
              className={`${styles.thumb} ${idx === activeIndex ? styles.thumbActive : ''}`}
              onClick={() => navigateTo(idx)}
              aria-label={`Изображение ${idx + 1}`}
              aria-current={idx === activeIndex ? 'true' : undefined}
            >
              <img src={img.url} alt={img.alt} className={styles.thumbImg} />
            </button>
          ))}
        </div>

        <div className={styles.main}>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={cropping ? handleCancelCrop : onClose}
            aria-label={cropping ? 'Отменить обрезку' : 'Закрыть'}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                d="M2 2L10 10M18 18L10 10M10 10L18 2M10 10L2 18"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </button>

          {cropping ? (
            <>
              <div className={styles.cropArea}>
                <ReactCrop
                  crop={crop}
                  aspect={aspect}
                  onChange={(c, percentCrop) => {
                    if (aspect) {
                      setCrop(percentCrop);
                      return;
                    }
                    const snap = 3;
                    const s = { ...percentCrop };
                    if (s.x < snap) {
                      s.width += s.x;
                      s.x = 0;
                    }
                    if (s.y < snap) {
                      s.height += s.y;
                      s.y = 0;
                    }
                    if (s.x + s.width > 100 - snap) s.width = 100 - s.x;
                    if (s.y + s.height > 100 - snap) s.height = 100 - s.y;
                    setCrop(s);
                  }}
                  onComplete={(c) => setCompletedCrop(c)}
                  keepSelection
                  ruleOfThirds
                >
                  {}
                  <img
                    ref={imgRef}
                    src={cropSrc}
                    alt={current.alt}
                    style={{
                      display: 'block',
                      maxWidth: '100%',
                      maxHeight: 'calc(85vh - 110px)',
                    }}
                  />
                </ReactCrop>
              </div>

              <div className={styles.cropToolbar}>
                <div className={styles.cropRatios}>
                  {ASPECT_RATIOS.map((r) => (
                    <button
                      key={r.label}
                      type="button"
                      className={
                        aspect === r.value
                          ? styles.cropRatioActive
                          : styles.cropRatio
                      }
                      onClick={() => handleAspectChange(r.value)}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
                <div className={styles.cropActions}>
                  <button
                    type="button"
                    className={styles.cropCancelBtn}
                    onClick={handleCancelCrop}
                  >
                    Отмена
                  </button>
                  <button
                    type="button"
                    className={styles.cropApplyBtn}
                    onClick={handleApplyCrop}
                    disabled={applying || !completedCrop?.width}
                  >
                    {applying ? 'Применяю...' : 'Применить'}
                  </button>
                </div>
                {cropError && (
                  <p className="text-app-danger mt-2 text-xs" role="alert">
                    {cropError}
                  </p>
                )}
              </div>
            </>
          ) : (
            <>
              {total > 1 && (
                <>
                  <button
                    type="button"
                    className={styles.arrowLeft}
                    onClick={goPrev}
                    aria-label="Предыдущее изображение"
                  >
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M15 5L8 12L15 19"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    className={styles.arrowRight}
                    onClick={goNext}
                    aria-label="Следующее изображение"
                  >
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M9 5L16 12L9 19"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </>
              )}

              <div className={styles.imageWrapper}>
                <img
                  src={previewUrl}
                  alt={current.alt}
                  className={styles.image}
                  draggable={false}
                />
                {/* No blocking spinner here on purpose — bg-removal is
                    fire-and-forget from the gallery thumbnail. Status
                    surfaces as a «Удаление фона» badge on the thumbnail,
                    same channel as the upload «Обработка» badge. */}
              </div>

              {bgRemovalState.status === 'completed' && (
                <div
                  role="group"
                  aria-label="Переключение фона"
                  style={{
                    position: 'absolute',
                    bottom: 80,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    display: 'flex',
                    gap: 4,
                    background: 'rgba(0,0,0,0.6)',
                    borderRadius: 9999,
                    padding: 4,
                    zIndex: 5,
                  }}
                >
                  <button
                    type="button"
                    onClick={handleToggleBgVariant}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 9999,
                      border: 'none',
                      background:
                        bgVariant === 'original' ? '#fff' : 'transparent',
                      color: bgVariant === 'original' ? '#000' : '#fff',
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    С фоном
                  </button>
                  <button
                    type="button"
                    onClick={handleToggleBgVariant}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 9999,
                      border: 'none',
                      background:
                        bgVariant === 'no-background' ? '#fff' : 'transparent',
                      color: bgVariant === 'no-background' ? '#000' : '#fff',
                      fontSize: 13,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    Без фона
                  </button>
                </div>
              )}

              {bgRemovalState.status === 'failed' && bgRemovalState.error && (
                <div
                  role="alert"
                  style={{
                    position: 'absolute',
                    bottom: 80,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: '#fee',
                    color: '#a02020',
                    padding: '8px 14px',
                    borderRadius: 8,
                    fontSize: 13,
                    maxWidth: 320,
                    textAlign: 'center',
                    zIndex: 5,
                  }}
                >
                  {bgRemovalState.error}
                </div>
              )}

              {/* Toolbar trimmed to «Обрезать» only. «Удалить фон» moved
                  to the gallery thumbnail (top-right, async/no-loader).
                  «Удалить изображение» moved to the thumbnail's top-left
                  X. Only the «Без фона / С фоном» toggle (rendered above)
                  stays inside the editor — that's the comparison surface
                  the merchandiser uses to validate the derivation. */}
              {canCrop && (
                <div className={styles.toolbar}>
                  <button
                    type="button"
                    className={styles.toolBtn}
                    onClick={handleStartCrop}
                    disabled={fetching}
                    aria-label="Обрезать изображение"
                  >
                    <svg
                      width="22"
                      height="22"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M6 2V6M6 6V19C6 19.5523 6.44772 20 7 20H18V24"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <path
                        d="M18 22V18M18 18V5C18 4.44772 17.5523 4 17 4H6V0"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
