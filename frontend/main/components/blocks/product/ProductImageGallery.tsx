"use client";
import React, { useState, TouchEvent, MouseEvent } from "react";
import Image from "next/image";
import styles from "./ProductImageGallery.module.css";
import cx from "clsx";

interface ProductImageGalleryProps {
  images: string[];
  productName: string;
  variant?: "carousel" | "strip";
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
  currentImageIndex?: number;
  onImageChange?: (index: number) => void;
}

export default function ProductImageGallery({
  images,
  productName,
  variant = "carousel",
  isFavorite = false,
  onToggleFavorite,
  currentImageIndex: externalImageIndex,
  onImageChange,
}: ProductImageGalleryProps) {
  const [internalImageIndex, setInternalImageIndex] = useState<number>(0);
  const currentImageIndex =
    externalImageIndex !== undefined ? externalImageIndex : internalImageIndex;

  const safeImageIndex = (() => {
    if (!Array.isArray(images) || images.length === 0) return 0;
    return Math.min(Math.max(currentImageIndex ?? 0, 0), images.length - 1);
  })();

  const setCurrentImageIndex = (index: number) => {
    const nextIndex = (() => {
      if (!Array.isArray(images) || images.length === 0) return 0;
      return Math.min(Math.max(index ?? 0, 0), images.length - 1);
    })();
    if (onImageChange) {
      onImageChange(nextIndex);
    } else {
      setInternalImageIndex(nextIndex);
    }
  };
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<number | null>(null);

  const minSwipeDistance = 50;

  if (variant === "strip") {
    return (
      <div className={styles.stripRoot} aria-label="\u0413\u0430\u043b\u0435\u0440\u0435\u044f">
        <div className={cx(styles.stripRow, "scrollbar-hide")}>
          {images.map((image, index) => (
            <button
              key={index}
              type="button"
              onClick={() => setCurrentImageIndex(index)}
              className={cx(
                styles.stripItem,
                index === safeImageIndex
                  ? styles.stripItemActive
                  : styles.stripItemInactive,
              )}
              aria-label={`\u0418\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 ${index + 1}`}
            >
              <Image
                src={image}
                alt={`${productName} - \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 ${index + 1}`}
                fill
                className={styles.stripImage}
                priority={index === safeImageIndex}
                sizes="82px"
              />
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Обработчики для тач-устройств
  const onTouchStartHandler = (e: TouchEvent<HTMLDivElement>) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMoveHandler = (e: TouchEvent<HTMLDivElement>) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEndHandler = () => {
    if (!touchStart || !touchEnd) return;

    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && safeImageIndex < images.length - 1) {
      setCurrentImageIndex(safeImageIndex + 1);
    }
    if (isRightSwipe && safeImageIndex > 0) {
      setCurrentImageIndex(safeImageIndex - 1);
    }
  };

  // Обработчики для мыши
  const onMouseDownHandler = (e: MouseEvent<HTMLDivElement>) => {
    setIsDragging(true);
    setDragStart(e.clientX);
  };

  const onMouseMoveHandler = () => {
    if (!isDragging || dragStart === null) return;
  };

  const onMouseUpHandler = (e: MouseEvent<HTMLDivElement>) => {
    if (!isDragging || dragStart === null) return;

    const distance = dragStart - e.clientX;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && safeImageIndex < images.length - 1) {
      setCurrentImageIndex(safeImageIndex + 1);
    }
    if (isRightSwipe && safeImageIndex > 0) {
      setCurrentImageIndex(safeImageIndex - 1);
    }

    setIsDragging(false);
    setDragStart(null);
  };

  const onMouseLeaveHandler = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  return (
    <div className={styles.c1}>
      <div
        className={styles.c2}
        onTouchStart={onTouchStartHandler}
        onTouchMove={onTouchMoveHandler}
        onTouchEnd={onTouchEndHandler}
        onMouseDown={onMouseDownHandler}
        onMouseMove={onMouseMoveHandler}
        onMouseUp={onMouseUpHandler}
        onMouseLeave={onMouseLeaveHandler}
      >
        {Array.isArray(images) && images.length > 0 ? (
          <div className={styles.c4} style={{ width: "100%", height: "100%" }}>
            <Image
              src={images[safeImageIndex]}
              alt={`${productName} - \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 ${safeImageIndex + 1}`}
              fill
              className={styles.c5}
              priority
              sizes="100vw"
            />
          </div>
        ) : null}

        {/* Кнопки избранного и поделиться */}
        <div className={styles.c6}>
          <div className={cx(styles.c7, styles.tw1)}>
            {/* Избранное */}
            <button
              onClick={onToggleFavorite}
              className={cx(styles.c8, styles.tw2)}
              aria-label={
                isFavorite ? "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0438\u0437 \u0438\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0433\u043e" : "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432 \u0438\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435"
              }
            >
              <Image
                src={
                  isFavorite
                    ? "/icons/global/active-heart.svg"
                    : "/icons/product/black-stroke-heart.svg"
                }
                alt="\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435"
                width={22}
                height={20}
                className={cx(styles.c9, styles.tw3)}
              />
            </button>

            {/* Поделиться */}
            <button
              className={cx(styles.c10, styles.tw4)}
              aria-label="\u041f\u043e\u0434\u0435\u043b\u0438\u0442\u044c\u0441\u044f"
            >
              <Image
                src="/icons/product/upload.svg"
                alt="\u041f\u043e\u0434\u0435\u043b\u0438\u0442\u044c\u0441\u044f"
                width={20}
                height={20}
                className={cx(styles.c11, styles.tw5)}
              />
            </button>
          </div>
        </div>
      </div>

      {Array.isArray(images) && images.length > 1 ? (
        <div className={styles.dotsWrap} aria-label="\u0421\u043b\u0430\u0439\u0434\u0435\u0440">
          {images.map((_, idx) => (
            <span
              key={idx}
              className={idx === safeImageIndex ? styles.dotActive : styles.dot}
              aria-hidden="true"
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
