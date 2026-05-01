'use client';

import { useEffect, useRef, useState } from 'react';
import ImageViewer from './ImageViewer';
import { ArrowIcon, SmallCloseIcon, UploadIcon } from './icons';
import styles from './styles/productForm.module.css';

const MAX_IMAGES = 10;
const ALLOWED_IMAGE_EXTENSIONS = /\.(jpe?g|png|gif|webp|avif|svg|bmp|tiff?)$/i;
const MIN_IMAGE_SIZE = 1024; // 1 KB minimum

export default function ImagesSection({
  images = [],
  onAdd,
  onRemove,
  onSet,
  uploads = {},
  onRetry,
  onImageCropped,
}) {
  const [urlValue, setUrlValue] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);
  const [urlError, setUrlError] = useState(''); // #7 — URL error message
  const [dragIndex, setDragIndex] = useState(null);
  const [dropIndex, setDropIndex] = useState(null);
  const [viewerIndex, setViewerIndex] = useState(null);
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
      // Skip files that are too small (likely corrupt or empty)
      if (file.size < MIN_IMAGE_SIZE) return;
      // Skip duplicates (same name + size)
      const isDuplicate = images.some(
        (img) => img.file?.name === file.name && img.file?.size === file.size,
      );
      if (isDuplicate) return;
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
    setUrlError('');
    if (!nextUrl || images.length >= MAX_IMAGES) return;
    if (!nextUrl.startsWith('https://') && !nextUrl.startsWith('http://')) {
      setUrlError('URL должен начинаться с http:// или https://');
      return;
    }
    try {
      const pathname = new URL(nextUrl).pathname;
      if (!ALLOWED_IMAGE_EXTENSIONS.test(pathname)) {
        setUrlError(
          'URL должен вести на изображение (.jpg, .png, .webp и т.д.)',
        );
        return;
      }
    } catch {
      setUrlError('Некорректный URL');
      return;
    }
    if (images.some((img) => img.url === nextUrl)) {
      setUrlError('Это изображение уже добавлено');
      return;
    }
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

  // #8 — Mobile reorder (move image up/down in list)
  function moveImage(fromIdx, toIdx) {
    if (toIdx < 0 || toIdx >= images.length) return;
    const reordered = [...images];
    const [moved] = reordered.splice(fromIdx, 1);
    reordered.splice(toIdx, 0, moved);
    onSet?.(reordered);
  }

  const imageCount = images.length;
  const hasImages = imageCount > 0;
  const canUploadMore = imageCount < MAX_IMAGES;
  const showUrlAction = Boolean(urlValue.trim());
  // Disable drag-reorder while any image is uploading/processing
  const anyUploading = images.some((img) => {
    const s = uploads[img.localId]?.status;
    return s === 'uploading' || s === 'processing';
  });

  return (
    <section className={styles.card}>
      <div className={styles.cardTitleMeta}>
        <h2 className={styles.cardTitle}>Изображения</h2>
        <p className={styles.cardSubtitle}>
          {hasImages
            ? `${imageCount} из ${MAX_IMAGES}`
            : `Не более ${MAX_IMAGES}`}
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
          aria-label="Выбрать файлы изображений"
        />

        {hasImages ? (
          <>
            <div
              className={styles.imagesGallery}
              role="list"
              aria-label="Галерея изображений товара"
            >
              {images.map((image, idx) => {
                const isDragging = dragIndex === idx;
                const isDropTarget = dropIndex === idx && dragIndex !== idx;

                const uploadState = uploads[image.localId];
                const isUploading = uploadState?.status === 'uploading';
                const isProcessing = uploadState?.status === 'processing';
                const isFailed = uploadState?.status === 'failed';

                return (
                  <div
                    key={image.localId}
                    className={styles.imagesGalleryItem}
                    draggable={!anyUploading}
                    role="listitem"
                    aria-label={`Изображение ${idx + 1} из ${imageCount}. Перетащите для изменения порядка`}
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, idx)}
                    onDragEnd={handleDragEnd}
                    style={{
                      opacity: isDragging ? 0.4 : 1,
                      outline: isDropTarget ? '2px dashed #000' : 'none',
                      outlineOffset: isDropTarget ? '-2px' : '0',
                      cursor: isUploading ? 'default' : 'grab',
                    }}
                  >
                    {idx === 0 && (
                      <span className={styles.imagesMainBadge}>Главное</span>
                    )}
                    <img
                      src={uploadState?.url || image.url}
                      alt={image.alt}
                      className={styles.imagesPreviewImage}
                      onClick={() => {
                        if (!isUploading) setViewerIndex(idx);
                      }}
                      style={{ cursor: isUploading ? 'default' : 'pointer' }}
                    />
                    {isUploading && (
                      <div className={styles.imagesUploadOverlay}>
                        <div className={styles.imagesUploadSpinner} />
                        {/* #15 — Show upload progress percentage */}
                        <span className={styles.imagesUploadLabel}>
                          {uploadState?.progress != null
                            ? `${Math.round(uploadState.progress)}%`
                            : 'Загрузка...'}
                        </span>
                        {uploadState?.progress != null && (
                          <div className={styles.uploadProgressBar}>
                            <div
                              className={styles.uploadProgressFill}
                              style={{
                                width: `${Math.round(uploadState.progress)}%`,
                              }}
                            />
                          </div>
                        )}
                      </div>
                    )}
                    {isProcessing && (
                      <span className={styles.imagesProcessingBadge}>
                        Обработка
                      </span>
                    )}
                    {isFailed && (
                      <div className={styles.imagesFailedBadge}>
                        <span className={styles.imagesFailedBadgeText}>
                          Ошибка
                        </span>
                        <button
                          type="button"
                          className={styles.imagesRetryButton}
                          onClick={(e) => {
                            e.stopPropagation();
                            onRetry?.(image);
                          }}
                        >
                          Повторить
                        </button>
                      </div>
                    )}
                    <button
                      type="button"
                      className={styles.imagesRemoveButton}
                      onClick={() => handleRemove(image.localId, image)}
                      aria-label="Удалить изображение"
                    >
                      <SmallCloseIcon />
                    </button>
                    {/* #8 — Mobile reorder buttons */}
                    {images.length > 1 && !anyUploading && (
                      <div className={styles.reorderButtons}>
                        <button
                          type="button"
                          className={styles.reorderButton}
                          disabled={idx === 0}
                          onClick={() => moveImage(idx, idx - 1)}
                          aria-label="Переместить вверх"
                        >
                          ◀
                        </button>
                        <button
                          type="button"
                          className={styles.reorderButton}
                          disabled={idx === images.length - 1}
                          onClick={() => moveImage(idx, idx + 1)}
                          aria-label="Переместить вниз"
                        >
                          ▶
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {canUploadMore ? (
              <button
                type="button"
                className={styles.imagesUploadBar}
                onClick={openFilePicker}
              >
                <span className={styles.imagesUploadBarIcon}>
                  <UploadIcon />
                </span>
                <span className={styles.imagesUploadBarText}>
                  Загрузить изображения
                </span>
              </button>
            ) : null}
          </>
        ) : (
          <button
            type="button"
            className={styles.uploadBox}
            onClick={openFilePicker}
          >
            <span className={styles.uploadIcon}>
              <UploadIcon />
            </span>
            <span className={styles.uploadText}>Загрузить изображения</span>
          </button>
        )}

        {canUploadMore ? (
          <>
            <div className={styles.sizeTableUrlRow}>
              <div
                className={
                  urlFocused
                    ? styles.sizeTableUrlFieldFocused
                    : styles.sizeTableUrlField
                }
              >
                <span className={styles.sizeTableUrlLabel}>URL картинки</span>
                <input
                  value={urlValue}
                  onChange={(event) => {
                    setUrlValue(event.target.value);
                    if (urlError) setUrlError('');
                  }}
                  onFocus={() => setUrlFocused(true)}
                  onBlur={() => setUrlFocused(false)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      applyUrlImage();
                    }
                  }}
                  className={styles.sizeTableUrlInput}
                  aria-label="URL изображения"
                />
              </div>
              {showUrlAction ? (
                <button
                  type="button"
                  className={styles.sizeTableUrlAction}
                  onClick={applyUrlImage}
                  aria-label="Загрузить изображение по URL"
                >
                  <ArrowIcon />
                </button>
              ) : null}
            </div>
            {urlError && <p className={styles.urlError}>{urlError}</p>}
          </>
        ) : null}
      </div>

      {viewerIndex !== null && (
        <ImageViewer
          images={images}
          uploads={uploads}
          initialIndex={viewerIndex}
          onClose={() => setViewerIndex(null)}
          onRemove={(localId, image) => {
            handleRemove(localId, image);
            if (images.length <= 1) setViewerIndex(null);
          }}
          onReplace={(localId, newImage) => {
            // Track new blob URLs for cleanup
            if (newImage.url?.startsWith('blob:')) {
              blobUrlsRef.current.add(newImage.url);
            }
            if (newImage.originalUrl?.startsWith('blob:')) {
              blobUrlsRef.current.add(newImage.originalUrl);
            }
            // Revoke old cropped blob URL, but NOT if it's the originalUrl
            const oldImage = images.find((img) => img.localId === localId);
            if (
              oldImage?.url?.startsWith('blob:') &&
              oldImage.url !== newImage.url &&
              oldImage.url !== newImage.originalUrl
            ) {
              URL.revokeObjectURL(oldImage.url);
              blobUrlsRef.current.delete(oldImage.url);
            }
            const updated = images.map((img) =>
              img.localId === localId ? newImage : img,
            );
            onSet?.(updated);
            onImageCropped?.(newImage);
          }}
        />
      )}
    </section>
  );
}
