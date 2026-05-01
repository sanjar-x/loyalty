'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { formatCurrency } from '@/shared/lib/utils';
import styles from './styles/productForm.module.css';

export default function ProductPreviewCard({
  title,
  brandName,
  price,
  images,
  uploads,
  isOriginal,
}) {
  const [activeIdx, setActiveIdx] = useState(0);
  const dragRef = useRef({ startX: 0, dragging: false });

  // Clamp index when images are removed
  useEffect(() => {
    if (images.length && activeIdx >= images.length) {
      setActiveIdx(images.length - 1);
    }
  }, [images.length, activeIdx]);

  const startSwipe = useCallback((x) => {
    dragRef.current = { startX: x, dragging: true };
  }, []);

  const endSwipe = useCallback(
    (x) => {
      if (!dragRef.current.dragging) return;
      dragRef.current.dragging = false;
      const diff = dragRef.current.startX - x;
      const threshold = 30;
      if (diff > threshold && activeIdx < images.length - 1) {
        setActiveIdx((i) => i + 1);
      } else if (diff < -threshold && activeIdx > 0) {
        setActiveIdx((i) => i - 1);
      }
    },
    [activeIdx, images.length],
  );

  const handleMouseDown = useCallback(
    (e) => {
      e.preventDefault();
      startSwipe(e.clientX);
    },
    [startSwipe],
  );
  const handleMouseUp = useCallback((e) => endSwipe(e.clientX), [endSwipe]);
  const handleTouchStart = useCallback(
    (e) => startSwipe(e.touches[0].clientX),
    [startSwipe],
  );
  const handleTouchEnd = useCallback(
    (e) => endSwipe(e.changedTouches[0].clientX),
    [endSwipe],
  );

  const numPrice = Number(price) || 0;
  const splitAmount = numPrice ? Math.ceil(numPrice / 4) : 0;
  const hasMultiple = images.length > 1;

  const swipeHandlers = hasMultiple
    ? {
        onMouseDown: handleMouseDown,
        onMouseUp: handleMouseUp,
        onTouchStart: handleTouchStart,
        onTouchEnd: handleTouchEnd,
      }
    : undefined;

  return (
    <section className={styles.previewCard}>
      <h2 className={styles.previewTitle}>Предпросмотр</h2>
      <div className={styles.previewPhone}>
        <div className={styles.previewScreen}>
          <div className={styles.previewImage} {...swipeHandlers}>
            <div
              className={styles.previewSlider}
              style={{ transform: `translateX(-${activeIdx * 100}%)` }}
            >
              {images.length > 0 ? (
                images.map((img) => (
                  <img
                    key={img.localId}
                    src={uploads?.[img.localId]?.url || img.url}
                    alt=""
                    className={styles.previewSlide}
                    draggable={false}
                  />
                ))
              ) : (
                <div className={styles.previewSlide} />
              )}
            </div>
            <span className={styles.previewHeart}>
              <svg
                width="30"
                height="27"
                viewBox="0 0 30 27"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M14.7174 6.0979C11.7802 -0.74505 1.5 -0.0162138 1.5 8.72986C1.5 17.4759 14.7174 24.7645 14.7174 24.7645C14.7174 24.7645 27.9348 17.4759 27.9348 8.72986C27.9348 -0.0162138 17.6546 -0.74505 14.7174 6.0979Z"
                  fill="white"
                  stroke="#B6B6B6"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
            {isOriginal && (
              <span className={styles.previewBadge}>ОРИГИНАЛ</span>
            )}
          </div>

          {hasMultiple && (
            <div className={styles.previewDots}>
              {images.map((img, i) => (
                <button
                  key={img.localId}
                  type="button"
                  className={
                    i === activeIdx
                      ? styles.previewDotActive
                      : styles.previewDot
                  }
                  onClick={() => setActiveIdx(i)}
                  aria-label={`Фото ${i + 1}`}
                />
              ))}
            </div>
          )}

          <div className={styles.previewMeta}>
            {numPrice ? (
              <>
                <p className={styles.previewPrice}>{formatCurrency(price)}</p>
                <p className={styles.previewSplit}>
                  <strong>
                    4×
                    {new Intl.NumberFormat('ru-RU').format(splitAmount)}
                  </strong>{' '}
                  в сплит
                </p>
              </>
            ) : (
              <>
                <div className={styles.previewTextLine} />
                <div className={styles.previewTextShort} />
              </>
            )}
          </div>
          <p className={styles.previewName}>{title}</p>
        </div>
      </div>
    </section>
  );
}
