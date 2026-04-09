'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactCrop from 'react-image-crop';
import { fetchImageAsFile } from '@/services/products';
import styles from './ImageViewer.module.css';

export default function ImageViewer({
  images,
  uploads = {},
  initialIndex = 0,
  onClose,
  onRemove,
  onReplace,
}) {
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const [cropping, setCropping] = useState(false);
  const [crop, setCrop] = useState(undefined);
  const [completedCrop, setCompletedCrop] = useState(null);
  const [applying, setApplying] = useState(false);
  const [aspect, setAspect] = useState(undefined);
  const [fetching, setFetching] = useState(false);
  const imgRef = useRef(null);

  const current = images[activeIndex];
  const total = images.length;

  // The source image for cropping: always the original (before any crop)
  const cropSrc = current?.originalUrl || current?.url;

  const goPrev = useCallback(() => {
    const prev = activeIndex > 0 ? activeIndex - 1 : total - 1;
    navigateTo(prev);
  }, [total, activeIndex]);

  const goNext = useCallback(() => {
    const next = activeIndex < total - 1 ? activeIndex + 1 : 0;
    navigateTo(next);
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
        onReplace?.(current.localId, {
          ...current,
          file,
          originalUrl: blobUrl,
          originalFile: file,
          url: blobUrl,
        });
      } catch {
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
      console.warn('Crop failed:', err);
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
      } catch {}
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

  function handleRemove() {
    onRemove?.(current.localId, current);
  }

  const canCrop = current.source === 'file' || current.source === 'url';

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
                  {/* eslint-disable-next-line @next/next/no-img-element */}
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
                  src={uploads[current.localId]?.url || current.url}
                  alt={current.alt}
                  className={styles.image}
                  draggable={false}
                />
              </div>

              <div className={styles.toolbar}>
                {canCrop && (
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
                )}
                <button
                  type="button"
                  className={styles.toolBtn}
                  onClick={handleRemove}
                  aria-label="Удалить изображение"
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
                      d="M3 6H5H21"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
