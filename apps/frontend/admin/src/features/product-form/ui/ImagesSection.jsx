'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ImageViewer from './ImageViewer';
import { ArrowIcon, SmallCloseIcon, UploadIcon } from './icons';
import { useImageReorder } from '../model/useImageReorder';
import { useBgRemoval } from '../model/useBgRemoval';
import styles from './styles/productForm.module.css';

// Resolve the storage object id we can run background-removal against.
// Eager uploads expose it via the upload state map; edit-mode images
// carry it on the image itself. No storage object → no derivation
// target → trigger button is disabled.
function resolveStorageObjectId(image, uploads) {
  if (!image) return null;
  return (
    uploads?.[image.localId]?.storageObjectId ?? image.storageObjectId ?? null
  );
}

function BgRemoveIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect
        x="3"
        y="3"
        width="18"
        height="18"
        rx="2"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="3 3"
      />
      <path
        d="M8 13L11 16L16 9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

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
  // Edit-mode-only: when present every reorder also POSTs to
  // /api/catalog/products/{id}/media/reorder. Create mode omits the
  // prop — reorder stays local until the product is saved.
  productId = null,
  // Shared bg-removal state (lifted to <ProductDetailsForm>) so the
  // gallery, the editor, and the right-hand <ProductPreviewCard> all
  // render the same derivation state. Falls back to a local instance
  // when the prop is omitted — keeps the component standalone for any
  // future caller that doesn't need the preview-card link.
  bgRemoval: bgRemovalProp,
}) {
  const [urlValue, setUrlValue] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);
  const [urlError, setUrlError] = useState(''); // #7 — URL error message
  const [dragIndex, setDragIndex] = useState(null);
  const [dropIndex, setDropIndex] = useState(null);
  const [viewerIndex, setViewerIndex] = useState(null);
  // ARIA live-region announcement string. Updated after every reorder so
  // screen readers learn the new position; the visual UI shows the
  // change directly.
  const [reorderAnnouncement, setReorderAnnouncement] = useState('');
  const fileInputRef = useRef(null);
  const blobUrlsRef = useRef(new Set());

  const { reorder: persistReorder, error: reorderError } = useImageReorder({
    productId,
    onLocalReorder: (next) => onSet?.(next),
  });

  // Lifted bg-removal state — survives modal close/reopen so the
  // merchandiser can keep working on other fields while derivation runs.
  // Parent may pass an instance to share state with the preview card;
  // otherwise we own a local one.
  const localBgRemoval = useBgRemoval();
  const bgRemoval = bgRemovalProp ?? localBgRemoval;

  const announceReorder = useCallback((image, fromIdx, toIdx, total) => {
    const label = image?.alt || 'Изображение';
    setReorderAnnouncement(
      `${label} перемещено с позиции ${fromIdx + 1} на ${toIdx + 1} из ${total}`,
    );
  }, []);

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
    persistReorder(images, reordered);
    announceReorder(moved, fromIdx, targetIdx, reordered.length);
  }

  function handleDragEnd() {
    setDragIndex(null);
    setDropIndex(null);
  }

  // Mobile + keyboard reorder (move image up/down in list).
  function moveImage(fromIdx, toIdx) {
    if (toIdx < 0 || toIdx >= images.length) return;
    const reordered = [...images];
    const [moved] = reordered.splice(fromIdx, 1);
    reordered.splice(toIdx, 0, moved);
    persistReorder(images, reordered);
    announceReorder(moved, fromIdx, toIdx, reordered.length);
  }

  // Keyboard alternative for drag-and-drop. Alt+ArrowUp / Alt+ArrowDown
  // swaps the focused image with its neighbour. Alt-modifier so plain
  // arrow-keys keep working for native focus traversal in the gallery.
  function handleImageKeyDown(e, idx) {
    if (!e.altKey) return;
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      moveImage(idx, idx - 1);
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      moveImage(idx, idx + 1);
    }
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
        {hasImages && (
          <p className={styles.cardSubtitle}>
            {imageCount} из {MAX_IMAGES}
          </p>
        )}
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

        {/* Visually-hidden polite announcer for reorder actions. */}
        <div
          aria-live="polite"
          aria-atomic="true"
          style={{
            position: 'absolute',
            width: 1,
            height: 1,
            padding: 0,
            margin: -1,
            overflow: 'hidden',
            clip: 'rect(0, 0, 0, 0)',
            whiteSpace: 'nowrap',
            border: 0,
          }}
        >
          {reorderAnnouncement}
        </div>

        {reorderError && (
          <div
            role="alert"
            className="text-app-danger mb-2 rounded-lg bg-red-50 px-3 py-2 text-sm"
          >
            Не удалось сохранить порядок изображений. Восстановили предыдущий
            порядок.
          </div>
        )}

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

                const storageObjectId = resolveStorageObjectId(image, uploads);
                const bgState = bgRemoval.stateByLocalId[image.localId];
                const bgStatus = bgState?.status ?? 'idle';
                const isBgRemoving = bgStatus === 'pending';
                const isBgRemoved = bgStatus === 'completed';
                const bgVariant =
                  bgRemoval.variantByLocalId[image.localId] ?? 'original';
                const showNoBg =
                  isBgRemoved &&
                  bgVariant === 'no-background' &&
                  Boolean(bgState?.derivedUrl);
                // Thumbnail prefers the derived no-background URL once
                // the derivation completes (variant defaults to
                // 'no-background' from the hook). Pre-fix the gallery
                // still rendered the original URL — the editor toggle
                // worked but the gallery never reflected it.
                const thumbnailSrc =
                  (showNoBg ? bgState.derivedUrl : null) ??
                  uploadState?.url ??
                  image.url;
                const canRemoveBg =
                  Boolean(storageObjectId) &&
                  bgStatus === 'idle' &&
                  !isUploading &&
                  !isProcessing &&
                  !isFailed;

                return (
                  <div
                    key={image.localId}
                    className={styles.imagesGalleryItem}
                    draggable={!anyUploading}
                    role="listitem"
                    tabIndex={anyUploading ? -1 : 0}
                    aria-label={`${image.alt || 'Изображение'}, позиция ${idx + 1} из ${imageCount}. Перетащите или Alt+стрелки для изменения порядка.`}
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, idx)}
                    onDragEnd={handleDragEnd}
                    onKeyDown={(e) => handleImageKeyDown(e, idx)}
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
                      src={thumbnailSrc}
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
                    {isBgRemoving && (
                      <span
                        className={styles.imagesBgRemovalBadge}
                        role="status"
                        aria-live="polite"
                      >
                        Удаление фона
                      </span>
                    )}
                    {!isProcessing && !isBgRemoving && isBgRemoved && (
                      <span className={styles.imagesBgRemovedBadge}>
                        Без фона
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
                    {/* BG-removal trigger lives on the thumbnail (not in the
                        editor) so the merchandiser can fire it without
                        opening a modal. Hidden once a derivation exists or
                        is in flight — the badges above take over the
                        top-right slot for those states. */}
                    {canRemoveBg && (
                      <button
                        type="button"
                        className={styles.imagesBgRemoveButton}
                        onClick={(e) => {
                          e.stopPropagation();
                          bgRemoval.requestRemoval(image, storageObjectId);
                        }}
                        aria-label="Удалить фон"
                        title="Удалить фон"
                      >
                        <BgRemoveIcon />
                      </button>
                    )}
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
          bgRemovalStateByLocalId={bgRemoval.stateByLocalId}
          bgVariantByLocalId={bgRemoval.variantByLocalId}
          onToggleBgVariant={bgRemoval.toggleVariant}
          onClose={() => setViewerIndex(null)}
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
