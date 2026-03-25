'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './page.module.css';

const MAX_IMAGES = 10;

function UploadIcon() {
  return (
    <svg width="12" height="24" viewBox="0 0 12 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M10.3636 5.45455V18C10.3636 20.4109 8.41091 22.3636 6 22.3636C3.58909 22.3636 1.63636 20.4109 1.63636 18V4.36364C1.63636 2.85818 2.85818 1.63636 4.36364 1.63636C5.86909 1.63636 7.09091 2.85818 7.09091 4.36364V15.8182C7.09091 16.4182 6.60545 16.9091 6 16.9091C5.39455 16.9091 4.90909 16.4182 4.90909 15.8182V5.45455H3.27273V15.8182C3.27273 17.3236 4.49455 18.5455 6 18.5455C7.50545 18.5455 8.72727 17.3236 8.72727 15.8182V4.36364C8.72727 1.95273 6.77455 0 4.36364 0C1.95273 0 0 1.95273 0 4.36364V18C0 21.3164 2.68909 24 6 24C9.31091 24 12 21.3164 12 18V5.45455H10.3636Z" fill="black"/>
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M5.8335 14H22.1668M22.1668 14L14.5835 6.41666M22.1668 14L14.5835 21.5833" stroke="black" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M0.75 0.75L5.75 5.75M10.75 10.75L5.75 5.75M5.75 5.75L10.3929 0.75M5.75 5.75L0.75 10.75" stroke="#7E7E7E" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export default function ImagesSection({ images = [], onAdd, onRemove, onSet }) {
  const [urlValue, setUrlValue] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);
  const [dragIndex, setDragIndex] = useState(null);
  const [dropIndex, setDropIndex] = useState(null);
  const fileInputRef = useRef(null);
  const blobUrlsRef = useRef(new Set());

  useEffect(() => {
    const blobUrls = blobUrlsRef.current;
    return () => {
      blobUrls.forEach((url) => URL.revokeObjectURL(url));
      blobUrls.clear();
    };
  }, []);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;
    const availableSlots = Math.max(MAX_IMAGES - images.length, 0);
    files.slice(0, availableSlots).forEach((file) => {
      const url = URL.createObjectURL(file);
      blobUrlsRef.current.add(url);
      onAdd?.({
        localId: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
        file,
        url,
        alt: file.name || 'Изображение товара',
        source: 'file',
      });
    });
    setUrlValue('');
    event.target.value = '';
  }

  function applyUrlImage() {
    const nextUrl = urlValue.trim();
    if (!nextUrl || images.length >= MAX_IMAGES) return;
    if (!nextUrl.startsWith('https://') && !nextUrl.startsWith('http://')) return;
    onAdd?.({
      localId: `url-${Date.now()}`,
      url: nextUrl,
      alt: 'Изображение товара по URL',
      source: 'url',
    });
    setUrlValue('');
  }

  function handleRemove(localId, image) {
    if (image.source === 'file' && image.url?.startsWith('blob:')) {
      URL.revokeObjectURL(image.url);
      blobUrlsRef.current.delete(image.url);
    }
    onRemove?.(localId);
  }

  // ── Drag-n-drop reorder ──

  function handleDragStart(e, idx) {
    setDragIndex(idx);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(idx));
  }

  function handleDragOver(e, idx) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (idx !== dropIndex) setDropIndex(idx);
  }

  function handleDragLeave() {
    setDropIndex(null);
  }

  function handleDrop(e, targetIdx) {
    e.preventDefault();
    const fromIdx = dragIndex;
    setDragIndex(null);
    setDropIndex(null);

    if (fromIdx === null || fromIdx === targetIdx) return;

    const reordered = [...images];
    const [moved] = reordered.splice(fromIdx, 1);
    reordered.splice(targetIdx, 0, moved);
    onSet?.(reordered);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDropIndex(null);
  }

  const imageCount = images.length;
  const hasImages = imageCount > 0;
  const canUploadMore = imageCount < MAX_IMAGES;
  const showUrlAction = Boolean(urlValue.trim());

  return (
    <section className={styles.card}>
      <div className={styles.cardTitleMeta}>
        <h2 className={styles.cardTitle}>Изображения</h2>
        <p className={styles.cardSubtitle}>
          {hasImages ? `${imageCount} из ${MAX_IMAGES}` : `Не более ${MAX_IMAGES}`}
        </p>
      </div>

      <div className={styles.imagesSectionBody}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className={styles.sizeTableFileInput}
          onChange={handleFileChange}
        />

        {hasImages ? (
          <>
            <div className={styles.imagesGallery}>
              {images.map((image, idx) => {
                const isDragging = dragIndex === idx;
                const isDropTarget = dropIndex === idx && dragIndex !== idx;

                return (
                  <div
                    key={image.localId}
                    className={styles.imagesGalleryItem}
                    draggable
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, idx)}
                    onDragEnd={handleDragEnd}
                    style={{
                      opacity: isDragging ? 0.4 : 1,
                      outline: isDropTarget ? '2px dashed #000' : 'none',
                      outlineOffset: isDropTarget ? '-2px' : '0',
                      cursor: 'grab',
                    }}
                  >
                    {idx === 0 && (
                      <span className={styles.imagesMainBadge}>Главное</span>
                    )}
                    <img
                      src={image.url}
                      alt={image.alt}
                      className={styles.imagesPreviewImage}
                    />
                    <button
                      type="button"
                      className={styles.imagesRemoveButton}
                      onClick={() => handleRemove(image.localId, image)}
                      aria-label="Удалить изображение"
                    >
                      <CloseIcon />
                    </button>
                  </div>
                );
              })}
            </div>

            {canUploadMore ? (
              <button type="button" className={styles.imagesUploadBar} onClick={openFilePicker}>
                <span className={styles.imagesUploadBarIcon}><UploadIcon /></span>
                <span className={styles.imagesUploadBarText}>Загрузить изображения</span>
              </button>
            ) : null}
          </>
        ) : (
          <button type="button" className={styles.uploadBox} onClick={openFilePicker}>
            <span className={styles.uploadIcon}><UploadIcon /></span>
            <span className={styles.uploadText}>Загрузить изображения</span>
          </button>
        )}

        {canUploadMore ? (
          <div className={styles.sizeTableUrlRow}>
            <div className={urlFocused ? styles.sizeTableUrlFieldFocused : styles.sizeTableUrlField}>
              <span className={styles.sizeTableUrlLabel}>URL картинки</span>
              <input
                value={urlValue}
                onChange={(event) => setUrlValue(event.target.value)}
                onFocus={() => setUrlFocused(true)}
                onBlur={() => setUrlFocused(false)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') { event.preventDefault(); applyUrlImage(); }
                }}
                className={styles.sizeTableUrlInput}
                aria-label="URL изображения"
              />
            </div>
            {showUrlAction ? (
              <button type="button" className={styles.sizeTableUrlAction} onClick={applyUrlImage} aria-label="Загрузить изображение по URL">
                <ArrowIcon />
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
