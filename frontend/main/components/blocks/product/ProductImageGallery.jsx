"use client";
import React, { useState } from "react";
import Image from "next/image";
import styles from "./ProductImageGallery.module.css";
import cx from "clsx";

export default function ProductImageGallery({
  images,
  productName,
  variant = "carousel",
  isFavorite = false,
  onToggleFavorite,
  currentImageIndex: externalImageIndex,
  onImageChange,
}) {
  const [internalImageIndex, setInternalImageIndex] = useState(0);
  const currentImageIndex =
    externalImageIndex !== undefined ? externalImageIndex : internalImageIndex;

  const safeImageIndex = (() => {
    if (!Array.isArray(images) || images.length === 0) return 0;
    return Math.min(Math.max(currentImageIndex ?? 0, 0), images.length - 1);
  })();

  const setCurrentImageIndex = (index) => {
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
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);

  const minSwipeDistance = 50;

  if (variant === "strip") {
    return (
      <div className={styles.stripRoot} aria-label="Галерея">
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
              aria-label={`Изображение ${index + 1}`}
            >
              <Image
                src={image}
                alt={`${productName} - изображение ${index + 1}`}
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
  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
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
  const onMouseDown = (e) => {
    setIsDragging(true);
    setDragStart(e.clientX);
  };

  const onMouseMove = () => {
    if (!isDragging || dragStart === null) return;
  };

  const onMouseUp = (e) => {
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

  const onMouseLeave = () => {
    setIsDragging(false);
    setDragStart(null);
  };

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
      >
        {Array.isArray(images) && images.length > 0 ? (
          <div className={styles.c4} style={{ width: "100%", height: "100%" }}>
            <Image
              src={images[safeImageIndex]}
              alt={`${productName} - изображение ${safeImageIndex + 1}`}
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
                isFavorite ? "Удалить из избранного" : "Добавить в избранное"
              }
            >
              <Image
                src={
                  isFavorite
                    ? "/icons/global/active-heart.svg"
                    : "/icons/product/black-stroke-heart.svg"
                }
                alt="Избранное"
                width={22}
                height={20}
                className={cx(styles.c9, styles.tw3)}
              />
            </button>

            {/* Поделиться */}
            <button
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
      </div>

      {Array.isArray(images) && images.length > 1 ? (
        <div className={styles.dotsWrap} aria-label="Слайдер">
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
