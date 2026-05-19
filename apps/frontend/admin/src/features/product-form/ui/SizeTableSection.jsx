'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowIcon, ChevronIcon, UploadIcon } from './icons';
import styles from './styles/productForm.module.css';

/**
 * Controlled size chart section.
 *
 * Props:
 *   value: { file?, url, source } | null — from useProductForm.state.sizeGuide
 *   onChange: (sizeGuide) => void — calls form.setField('sizeGuide', ...)
 */

export default function SizeTableSection({ value = null, onChange }) {
  const [open, setOpen] = useState(false);
  const [urlValue, setUrlValue] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);
  const fileInputRef = useRef(null);
  const blobUrlRef = useRef(null);

  const previewUrl = value?.url ?? '';

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);

    const url = URL.createObjectURL(file);
    blobUrlRef.current = url;
    onChange?.({ file, url, source: 'file' });
    setUrlValue('');
    event.target.value = '';
  }

  function applyUrlImage() {
    const nextUrl = urlValue.trim();
    if (!nextUrl) return;
    if (!nextUrl.startsWith('https://') && !nextUrl.startsWith('http://'))
      return;

    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }

    onChange?.({ url: nextUrl, source: 'url' });
    setUrlValue('');
  }

  const showUrlAction = Boolean(urlValue.trim());

  return (
    <section className={styles.sizeTableCard}>
      <button
        type="button"
        className={styles.sizeTableHeader}
        onClick={() => setOpen((c) => !c)}
        aria-expanded={open}
      >
        <h2 className={styles.sizeTableTitle}>Таблица размеров</h2>
        <span
          className={
            open ? styles.sizeTableChevronOpen : styles.sizeTableChevron
          }
        >
          <ChevronIcon />
        </span>
      </button>

      {open ? (
        <div className={styles.sizeTableBody}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className={styles.sizeTableFileInput}
            onChange={handleFileChange}
          />

          {previewUrl ? (
            <button
              type="button"
              className={styles.sizeTablePreviewButton}
              onClick={openFilePicker}
            >
              <img
                src={previewUrl}
                alt="Таблица размеров"
                className={styles.sizeTablePreviewImage}
              />
            </button>
          ) : (
            <button
              type="button"
              className={styles.sizeTableUploadBox}
              onClick={openFilePicker}
            >
              <span className={styles.sizeTableUploadIcon}>
                <UploadIcon />
              </span>
              <span className={styles.sizeTableUploadText}>
                Загрузить изображение
              </span>
            </button>
          )}

          {!previewUrl ? (
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
                  onChange={(e) => setUrlValue(e.target.value)}
                  onFocus={() => setUrlFocused(true)}
                  onBlur={() => setUrlFocused(false)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      applyUrlImage();
                    }
                  }}
                  className={styles.sizeTableUrlInput}
                  aria-label="URL таблицы размеров"
                />
              </div>
              {showUrlAction ? (
                <button
                  type="button"
                  className={styles.sizeTableUrlAction}
                  onClick={applyUrlImage}
                  aria-label="Загрузить таблицу размеров по URL"
                >
                  <ArrowIcon />
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
