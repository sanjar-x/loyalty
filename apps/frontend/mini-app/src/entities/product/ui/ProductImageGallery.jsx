'use client';
import React, { useState, useRef, useCallback } from 'react';
import Image from 'next/image';

import { useDragToScroll } from '@/shared/lib/hooks';
import styles from './ProductImageGallery.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';

export default function ProductImageGallery({
  images,
  productName,
  variant = 'carousel',
  isFavorite = false,
  onToggleFavorite,
  onShare,
  currentImageIndex: externalImageIndex,
  onImageChange,
  priorityFirst = false,
}) {
  const [internalImageIndex, setInternalImageIndex] = useState(0);
  const currentImageIndex =
    externalImageIndex !== undefined ? externalImageIndex : internalImageIndex;

  // Desktop swipe — the hook is disabled automatically on touch. The hook is
  // called on every render (Rules of Hooks); React handles changes to `variant`
  // safely. `ref` is attached only to the `<div>` in the strip variant.
  const stripRowRef = useDragToScroll();

  const safeImages = Array.isArray(images) ? images : [];
  const count = safeImages.length;

  const safeIndex = count > 0 ? Math.min(Math.max(currentImageIndex ?? 0, 0), count - 1) : 0;

  const setIndex = useCallback(
    (next) => {
      const clamped = Math.min(Math.max(next, 0), count - 1);
      if (onImageChange) onImageChange(clamped);
      else setInternalImageIndex(clamped);
    },
    [count, onImageChange]
  );

  // ── Touch / drag state ───────────────────────────────────────────────────
  const touchStartX = useRef(null);
  const dragDelta = useRef(0);
  const [liveOffset, setLiveOffset] = useState(0); // px offset during drag
  const MIN_SWIPE = 50;

  const onTouchStart = (e) => {
    touchStartX.current = e.targetTouches[0].clientX;
    dragDelta.current = 0;
    setLiveOffset(0);
  };

  const onTouchMove = (e) => {
    if (touchStartX.current === null) return;
    const delta = e.targetTouches[0].clientX - touchStartX.current;
    dragDelta.current = delta;
    // Resist at edges
    const atLeft = safeIndex === 0 && delta > 0;
    const atRight = safeIndex === count - 1 && delta < 0;
    setLiveOffset(atLeft || atRight ? delta * 0.25 : delta);
  };

  const onTouchEnd = () => {
    const d = dragDelta.current;
    if (d < -MIN_SWIPE && safeIndex < count - 1) setIndex(safeIndex + 1);
    else if (d > MIN_SWIPE && safeIndex > 0) setIndex(safeIndex - 1);
    touchStartX.current = null;
    dragDelta.current = 0;
    setLiveOffset(0);
  };

  // ── Mouse drag ───────────────────────────────────────────────────────────
  const mouseStartX = useRef(null);

  const onMouseDown = (e) => {
    mouseStartX.current = e.clientX;
    dragDelta.current = 0;
    setLiveOffset(0);
  };

  const onMouseMove = (e) => {
    if (mouseStartX.current === null) return;
    const delta = e.clientX - mouseStartX.current;
    dragDelta.current = delta;
    setLiveOffset(delta);
  };

  const onMouseUp = () => {
    const d = dragDelta.current;
    if (d < -MIN_SWIPE && safeIndex < count - 1) setIndex(safeIndex + 1);
    else if (d > MIN_SWIPE && safeIndex > 0) setIndex(safeIndex - 1);
    mouseStartX.current = null;
    dragDelta.current = 0;
    setLiveOffset(0);
  };

  const onMouseLeave = () => {
    if (mouseStartX.current === null) return;
    mouseStartX.current = null;
    dragDelta.current = 0;
    setLiveOffset(0);
  };

  // ── strip variant ────────────────────────────────────────────────────────
  if (variant === 'strip') {
    return (
      <div className={styles.stripRoot} aria-label="Галерея">
        <div ref={stripRowRef} className={cx(styles.stripRow, 'scrollbar-hide')}>
          {safeImages.map((image, index) => (
            <button
              key={index}
              type="button"
              onClick={() => setIndex(index)}
              className={cx(
                styles.stripItem,
                index === safeIndex ? styles.stripItemActive : styles.stripItemInactive
              )}
              aria-label={`Изображение ${index + 1}`}
            >
              <Image
                src={image}
                alt={`${productName} - изображение ${index + 1}`}
                fill
                className={styles.stripImage}
                priority={index === safeIndex}
                sizes="82px"
              />
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ── carousel variant ─────────────────────────────────────────────────────
  // Base translate is -safeIndex * 100%. Live drag adds pixel offset on top.
  const translateX =
    liveOffset !== 0 ? `calc(${-safeIndex * 100}% + ${liveOffset}px)` : `${-safeIndex * 100}%`;

  const isAnimating = liveOffset === 0;

  return (
    <div className={styles.c1}>
      <div
        className={styles.c2}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
        style={{ cursor: mouseStartX.current !== null ? 'grabbing' : 'grab' }}
        aria-label="Галерея изображений"
        role="region"
      >
        {/* Sliding strip — all images in a row */}
        <div
          className={styles.strip}
          style={{
            transform: `translateX(${translateX})`,
            transition: isAnimating ? 'transform 280ms cubic-bezier(0.25,0.46,0.45,0.94)' : 'none',
          }}
        >
          {safeImages.map((src, idx) => (
            <div key={idx} className={styles.slide}>
              <Image
                src={src}
                alt={`${productName ?? ''} — ${idx + 1}`}
                fill
                className={styles.c5}
                priority={priorityFirst ? idx === 0 : idx === safeIndex}
                sizes="100vw"
                draggable={false}
              />
            </div>
          ))}
        </div>

        {/* Favourite + Share buttons */}
        <div className={styles.c6}>
          <div className={cx(styles.c7, styles.tw1)}>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleFavorite?.();
              }}
              className={cx(styles.c8, styles.tw2)}
              aria-label={isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
            >
              <Image
                src={
                  isFavorite
                    ? '/icons/global/active-heart.svg'
                    : '/icons/product/black-stroke-heart.svg'
                }
                alt="Избранное"
                width={22}
                height={20}
                className={cx(styles.c9, styles.tw3)}
              />
            </button>

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onShare?.();
              }}
              className={cx(styles.c10, styles.tw4)}
              aria-label="Поделиться"
            >
              <Image
                src="/icons/product/upload.svg"
                alt="Поделиться"
                width={20}
                height={20}
                className={cx(styles.c11, styles.tw5)}
              />
            </button>
          </div>
        </div>

        {/* Dots — inside container, bottom-center */}
        {count > 1 && (
          <div className={styles.dotsWrap} aria-label="Слайдер">
            {safeImages.map((_, idx) => (
              <button
                key={idx}
                type="button"
                className={cx(styles.dot, idx === safeIndex && styles.dotActive)}
                aria-label={`Слайд ${idx + 1}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setIndex(idx);
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
