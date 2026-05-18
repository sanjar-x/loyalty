'use client';
import Image from 'next/image';
import { memo, useCallback, useRef, useState } from 'react';

import styles from './ProductImageCarousel.module.css';

/**
 * Native CSS scroll-snap carousel.
 * - Both touch swipe and mouse drag work (browser native).
 * - Tap vs swipe disambiguation: if pointerdown/up delta > 8px, `onTap` is not
 *   called (to avoid triggering the card click).
 * - Fallback: if there is only 1 image, a static <Image/> is rendered with no scroll.
 */
function ProductImageCarousel({
  images,
  alt = '',
  sizes = '(max-width: 768px) 50vw, 200px',
  onTap,
  onImageError,
  onActiveChange,
}) {
  const trackRef = useRef(null);
  const [activeIdx, setActiveIdx] = useState(0);

  const pointerStart = useRef(null);
  const didSwipe = useRef(false);
  const isMouseDrag = useRef(false);
  const rafId = useRef(0);
  const pendingDx = useRef(0);
  const scrollRaf = useRef(0);

  const list = Array.isArray(images) ? images.filter(Boolean) : [];
  const multi = list.length > 1;

  const handleScroll = useCallback(() => {
    if (scrollRaf.current) return;
    scrollRaf.current = requestAnimationFrame(() => {
      scrollRaf.current = 0;
      const el = trackRef.current;
      if (!el) return;
      const w = el.clientWidth || 1;
      const idx = Math.round(el.scrollLeft / w);
      const clamped = Math.max(0, Math.min(list.length - 1, idx));
      setActiveIdx((prev) => (prev === clamped ? prev : clamped));
      onActiveChange?.(clamped);
    });
  }, [list.length, onActiveChange]);

  const snapToNearest = useCallback(() => {
    const el = trackRef.current;
    if (!el) return;
    const w = el.clientWidth || 1;
    const idx = Math.round(el.scrollLeft / w);
    el.scrollTo({ left: idx * w, behavior: 'smooth' });
  }, []);

  const onPointerDown = useCallback((e) => {
    pointerStart.current = {
      x: e.clientX,
      y: e.clientY,
      t: Date.now(),
      scrollLeft: trackRef.current?.scrollLeft ?? 0,
    };
    didSwipe.current = false;
    if (e.pointerType === 'mouse') {
      isMouseDrag.current = true;
      try {
        e.currentTarget.setPointerCapture?.(e.pointerId);
      } catch {
        /* noop */
      }
    }
  }, []);

  const onPointerMove = useCallback((e) => {
    const s = pointerStart.current;
    if (!s) return;
    const dx = e.clientX - s.x;
    if (Math.abs(dx) > 6) didSwipe.current = true;
    if (isMouseDrag.current && trackRef.current) {
      pendingDx.current = dx;
      if (!rafId.current) {
        rafId.current = requestAnimationFrame(() => {
          rafId.current = 0;
          const el = trackRef.current;
          if (!el || !pointerStart.current) return;
          el.scrollLeft = pointerStart.current.scrollLeft - pendingDx.current;
        });
      }
    }
  }, []);

  const onPointerUp = useCallback(
    (e) => {
      const s = pointerStart.current;
      pointerStart.current = null;
      const wasMouseDrag = isMouseDrag.current;
      isMouseDrag.current = false;
      if (rafId.current) {
        cancelAnimationFrame(rafId.current);
        rafId.current = 0;
      }
      if (!s) return;
      const dx = Math.abs(e.clientX - s.x);
      const dy = Math.abs(e.clientY - s.y);
      const dt = Date.now() - s.t;
      if (wasMouseDrag) {
        try {
          e.currentTarget.releasePointerCapture?.(e.pointerId);
        } catch {
          /* noop */
        }
        if (didSwipe.current) {
          snapToNearest();
          e.preventDefault();
          e.stopPropagation();
          return;
        }
      }
      if (!didSwipe.current && dx < 6 && dy < 6 && dt < 400) {
        onTap?.(e);
      }
    },
    [onTap, snapToNearest]
  );

  const onPointerCancel = useCallback(() => {
    pointerStart.current = null;
    didSwipe.current = false;
    isMouseDrag.current = false;
    if (rafId.current) {
      cancelAnimationFrame(rafId.current);
      rafId.current = 0;
    }
  }, []);

  const onClickCapture = useCallback((e) => {
    // Swallow the click that fires after a mouse drag ends
    if (didSwipe.current) {
      e.preventDefault();
      e.stopPropagation();
      didSwipe.current = false;
    }
  }, []);

  // Accessibility for arrow-key navigation
  const onKeyDown = useCallback(
    (e) => {
      if (!multi) return;
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      const el = trackRef.current;
      if (!el) return;
      e.preventDefault();
      const dir = e.key === 'ArrowRight' ? 1 : -1;
      const next = Math.max(0, Math.min(list.length - 1, activeIdx + dir));
      el.scrollTo({ left: next * el.clientWidth, behavior: 'smooth' });
    },
    [activeIdx, list.length, multi]
  );

  if (list.length === 0) return null;

  if (!multi) {
    return (
      <Image
        src={list[0]}
        alt={alt}
        className={styles.image}
        fill
        sizes={sizes}
        loading="lazy"
        onError={onImageError}
        onClick={onTap}
      />
    );
  }

  return (
    <div
      className={styles.wrap}
      role="region"
      aria-roledescription="carousel"
      aria-label={alt || 'Product images'}
    >
      <div
        ref={trackRef}
        className={styles.track}
        onScroll={handleScroll}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerCancel}
        onClickCapture={onClickCapture}
        onKeyDown={onKeyDown}
        tabIndex={-1}
      >
        {list.map((src, i) => {
          // Only eager-load nearby slides
          const near = Math.abs(i - activeIdx) <= 1;
          return (
            <div key={`${i}-${src}`} className={styles.slide}>
              <Image
                src={src}
                alt={i === 0 ? alt : ''}
                className={styles.image}
                fill
                sizes={sizes}
                loading={near ? 'eager' : 'lazy'}
                fetchPriority={i === 0 ? 'high' : 'auto'}
                onError={onImageError}
                draggable={false}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default memo(ProductImageCarousel);
