'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactCrop from 'react-image-crop';
import styles from './ImageViewer.module.css';

export default function ImageViewer({ images, initialIndex = 0, onClose, onRemove, onReplace }) {
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const [cropping, setCropping] = useState(false);
  const [crop, setCrop] = useState(undefined);
  const [completedCrop, setCompletedCrop] = useState(null);
  const [applying, setApplying] = useState(false);
  const imgRef = useRef(null);

  const current = images[activeIndex];
  const total = images.length;

  // The source image for cropping: always the original (before any crop)
  const cropSrc = current?.originalUrl || current?.url;

  const goPrev = useCallback(() => {
    if (cropping) return;
    setActiveIndex((i) => (i > 0 ? i - 1 : total - 1));
  }, [total, cropping]);

  const goNext = useCallback(() => {
    if (cropping) return;
    setActiveIndex((i) => (i < total - 1 ? i + 1 : 0));
  }, [total, cropping]);

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
      if (!cropping) {
        if (e.key === 'ArrowLeft') goPrev();
        if (e.key === 'ArrowRight') goNext();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [onClose, goPrev, goNext, cropping]);

  useEffect(() => {
    if (activeIndex >= total) setActiveIndex(Math.max(0, total - 1));
  }, [total, activeIndex]);

  useEffect(() => {
    if (!images || images.length === 0) onClose();
  }, [images, onClose]);

  if (!current || total === 0) return null;

  function handleStartCrop() {
    if (current.source === 'url' && !current.file) return;
    // Restore last crop state, or start at 100%
    setCrop(current.lastCrop || { unit: '%', x: 0, y: 0, width: 100, height: 100 });
    setCompletedCrop(null);
    setCropping(true);
  }

  function handleCancelCrop() {
    setCropping(false);
    setCrop(undefined);
    setCompletedCrop(null);
  }

  async function handleApplyCrop() {
    const image = imgRef.current;
    const c = completedCrop;
    if (!image || !c?.width || !c?.height) return;

    setApplying(true);
    try {
      const canvas = document.createElement('canvas');
      const scaleX = image.naturalWidth / image.width;
      const scaleY = image.naturalHeight / image.height;

      canvas.width = c.width * scaleX;
      canvas.height = c.height * scaleY;

      const ctx = canvas.getContext('2d');
      ctx.drawImage(
        image,
        c.x * scaleX,
        c.y * scaleY,
        c.width * scaleX,
        c.height * scaleY,
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
      const newFile = new File([blob], current.file?.name || 'cropped.jpg', {
        type: 'image/jpeg',
      });

      onReplace?.(current.localId, {
        ...current,
        file: newFile,
        url: newUrl,
        source: 'file',
        // Preserve the original for future re-crops
        originalUrl: current.originalUrl || current.url,
        originalFile: current.originalFile || current.file,
        lastCrop: crop,
      });

      setCropping(false);
      setCrop(undefined);
      setCompletedCrop(null);
    } catch (err) {
      console.warn('Crop failed:', err);
    } finally {
      setApplying(false);
    }
  }

  function handleRemove() {
    onRemove?.(current.localId, current);
  }

  const canCrop = current.source === 'file' || (current.source === 'url' && current.file);

  return (
    <div className={styles.overlay} onClick={cropping ? undefined : onClose} role="dialog" aria-label="Просмотр изображения">
      <div className={styles.container} onClick={(e) => e.stopPropagation()}>
        <div className={styles.sidebar}>
          {images.map((img, idx) => (
            <button
              key={img.localId}
              type="button"
              className={`${styles.thumb} ${idx === activeIndex ? styles.thumbActive : ''}`}
              onClick={() => { if (!cropping) setActiveIndex(idx); }}
              aria-label={`Изображение ${idx + 1}`}
              aria-current={idx === activeIndex ? 'true' : undefined}
              disabled={cropping}
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
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <path d="M2 2L10 10M18 18L10 10M10 10L18 2M10 10L2 18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          </button>

          {cropping ? (
            <>
              <div className={styles.cropArea}>
                <ReactCrop
                  crop={crop}
                  onChange={(c, percentCrop) => {
                    const snap = 3;
                    const s = { ...percentCrop };
                    if (s.x < snap) { s.width += s.x; s.x = 0; }
                    if (s.y < snap) { s.height += s.y; s.y = 0; }
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
                <div className={styles.cropActions}>
                  <button type="button" className={styles.cropCancelBtn} onClick={handleCancelCrop}>
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
                  <button type="button" className={styles.arrowLeft} onClick={goPrev} aria-label="Предыдущее изображение">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path d="M15 5L8 12L15 19" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                  <button type="button" className={styles.arrowRight} onClick={goNext} aria-label="Следующее изображение">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path d="M9 5L16 12L9 19" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                </>
              )}

              <div className={styles.imageWrapper}>
                <img src={current.url} alt={current.alt} className={styles.image} draggable={false} />
              </div>

              <div className={styles.toolbar}>
                {canCrop && (
                  <button type="button" className={styles.toolBtn} onClick={handleStartCrop} aria-label="Обрезать изображение">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <path d="M6 2V6M6 6V19C6 19.5523 6.44772 20 7 20H18V24" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M18 22V18M18 18V5C18 4.44772 17.5523 4 17 4H6V0" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                )}
                <button type="button" className={styles.toolBtn} onClick={handleRemove} aria-label="Удалить изображение">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path d="M3 6H5H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
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
