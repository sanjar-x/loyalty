'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { groupBrandsByLetter, useBrands, useCreateBrand } from '@/entities/brand';
import {
  confirmMedia,
  extractRawUrl,
  reserveMediaUpload,
  subscribeMediaStatus,
  uploadToS3,
} from '@/entities/product';
import { genId } from '@/shared/lib/genId';
import { ChevronIcon, UploadIcon } from './icons';
import styles from './styles/productForm.module.css';

function PlusIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M15 6.25C15.5178 6.25 15.9375 6.66973 15.9375 7.1875V14.0625H22.8125C23.3303 14.0625 23.75 14.4822 23.75 15C23.75 15.5178 23.3303 15.9375 22.8125 15.9375H15.9375V22.8125C15.9375 23.3303 15.5178 23.75 15 23.75C14.4822 23.75 14.0625 23.3303 14.0625 22.8125V15.9375H7.1875C6.66973 15.9375 6.25 15.5178 6.25 15C6.25 14.4822 6.66973 14.0625 7.1875 14.0625H14.0625V7.1875C14.0625 6.66973 14.4822 6.25 15 6.25Z"
        fill="black"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M7.2728 6.21214C6.9799 5.91924 6.50503 5.91924 6.21214 6.21214C5.91924 6.50503 5.91924 6.9799 6.21214 7.2728L13.9393 15L6.21214 22.7272C5.91924 23.0201 5.91924 23.495 6.21214 23.7879C6.50503 24.0808 6.9799 24.0808 7.2728 23.7879L15 16.0607L22.7272 23.7879C23.0201 24.0808 23.495 24.0808 23.7879 23.7879C24.0808 23.495 24.0808 23.0201 23.7879 22.7272L16.0607 15L23.7879 7.2728C24.0808 6.9799 24.0808 6.50503 23.7879 6.21214C23.495 5.91924 23.0201 5.91924 22.7272 6.21214L15 13.9393L7.2728 6.21214Z"
        fill="black"
      />
    </svg>
  );
}

function BrandMark({ brand }) {
  if (brand.logoUrl) {
    return (
      <div className={styles.brandOptionLogo} aria-hidden="true">
        <img
          src={brand.logoUrl}
          alt=""
          className={styles.brandOptionLogoImage}
        />
      </div>
    );
  }

  const mark = brand.mark ?? brand.name?.slice(0, 3)?.toUpperCase() ?? '';
  return (
    <div className={styles.brandOptionLogo} aria-hidden="true">
      <span className={styles.brandOptionLogoText}>{mark}</span>
    </div>
  );
}

export default function BrandSelect({ value, onChange, hasError = false }) {
  const {
    data: brandsData,
    isPending: brandsInitialLoading,
    isError: brandsLoadError,
    refetch: refetchBrands,
  } = useBrands();
  const createBrandMutation = useCreateBrand();
  // Show the spinner only on the very first load (no cache yet).
  // Background refetches keep the previous data visible.
  const brandsLoading = brandsInitialLoading && !brandsData;

  const brands = useMemo(() => brandsData?.items ?? [], [brandsData]);
  const brandSections = useMemo(() => groupBrandsByLetter(brands), [brands]);

  const [open, setOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Derive selectedBrand from value prop + loaded brands list
  const selectedBrand = value
    ? (brands.find((b) => b.id === value) ?? null)
    : null;

  // Filter brand sections by search query
  const filteredSections = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return brandSections;
    return brandSections
      .map((section) => ({
        ...section,
        brands: section.brands.filter((b) => b.name?.toLowerCase().includes(q)),
      }))
      .filter((section) => section.brands.length > 0);
  }, [brandSections, searchQuery]);
  // #13 — Active index for keyboard navigation
  const [activeIndex, setActiveIndex] = useState(-1);
  const flatFilteredBrands = useMemo(
    () => filteredSections.flatMap((s) => s.brands),
    [filteredSections],
  );

  function handleDropdownKeyDown(event) {
    if (!open) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatFilteredBrands.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      const brand = flatFilteredBrands[activeIndex];
      if (brand) {
        onChange?.(brand);
        setOpen(false);
      }
    }
  }

  const [brandImagePreviewUrl, setBrandImagePreviewUrl] = useState('');
  const [brandImageName, setBrandImageName] = useState('');
  const [brandImageFile, setBrandImageFile] = useState(null); // #3 — keep actual File for upload
  const [newBrandName, setNewBrandName] = useState('');
  const [newBrandDescription, setNewBrandDescription] = useState(''); // #20
  const [newBrandWebsite, setNewBrandWebsite] = useState(''); // #20
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const fileInputRef = useRef(null);
  const rootRef = useRef(null);
  const modalRef = useRef(null); // #14 — for focus trap
  // Aborts in-flight SSE / POST when the user closes the modal mid-upload.
  const createAbortRef = useRef(null);

  useEffect(() => {
    return () => {
      createAbortRef.current?.abort();
    };
  }, []);

  const isBrandFormComplete = Boolean(newBrandName.trim());

  useEffect(() => {
    return () => {
      if (brandImagePreviewUrl) {
        URL.revokeObjectURL(brandImagePreviewUrl);
      }
    };
  }, [brandImagePreviewUrl]);

  useEffect(() => {
    if (!open && !isAddModalOpen) {
      return;
    }

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
        setIsAddModalOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setIsAddModalOpen(false);
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open, isAddModalOpen]);

  // #14 — Focus trap for brand creation modal
  useEffect(() => {
    if (!isAddModalOpen) return;
    const modal = modalRef.current;
    if (!modal) return;

    function handleTabTrap(e) {
      if (e.key !== 'Tab') return;
      const focusable = modal.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    modal.addEventListener('keydown', handleTabTrap);
    // Auto-focus first focusable element
    const firstFocusable = modal.querySelector(
      'input:not([type="file"]), button',
    );
    firstFocusable?.focus();

    return () => modal.removeEventListener('keydown', handleTabTrap);
  }, [isAddModalOpen]);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function openAddBrandModal() {
    setOpen(false);
    setNewBrandName('');
    setBrandImagePreviewUrl('');
    setBrandImageName('');
    setCreateError('');
    setIsAddModalOpen(true);
  }

  function closeAddBrandModal() {
    createAbortRef.current?.abort();
    createAbortRef.current = null;
    setIsAddModalOpen(false);
  }

  function handleBrandImageChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (brandImagePreviewUrl) {
      URL.revokeObjectURL(brandImagePreviewUrl);
    }

    const previewUrl = URL.createObjectURL(file);
    setBrandImagePreviewUrl(previewUrl);
    setBrandImageName(file.name);
    setBrandImageFile(file); // #3 — keep File reference
    event.target.value = '';
  }

  async function handleCreateBrand() {
    if (!newBrandName.trim() || creating) return;
    setCreating(true);
    setCreateError('');

    const controller = new AbortController();
    createAbortRef.current?.abort();
    createAbortRef.current = controller;
    const { signal } = controller;

    const slug = newBrandName
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9а-яё]+/gi, '-')
      .replace(/^-+|-+$/g, '');

    try {
      // #3 — Upload logo to server if a file was selected
      let logoUrl = null;
      if (brandImageFile) {
        const reserve = await reserveMediaUpload({
          contentType: brandImageFile.type,
          filename: brandImageFile.name,
        });
        if (signal.aborted) return;
        const { presignedUrl, storageObjectId } = reserve;
        await uploadToS3(presignedUrl, brandImageFile);
        if (signal.aborted) return;
        await confirmMedia(storageObjectId);
        if (signal.aborted) return;
        // Wait for processing — abort-aware so closing the modal cleans up SSE.
        try {
          await subscribeMediaStatus(storageObjectId, {
            timeout: 30000,
            signal,
          });
        } catch (err) {
          if (err?.name === 'AbortError') return;
          /* proceed even if SSE times out */
        }
        logoUrl = extractRawUrl(presignedUrl);
      }

      const body = {
        name: newBrandName.trim(),
        slug: slug || genId('brand'),
      };
      // #20 — Send optional extra fields
      if (newBrandDescription.trim())
        body.description = newBrandDescription.trim();
      if (newBrandWebsite.trim()) body.websiteUrl = newBrandWebsite.trim();
      if (logoUrl) body.logoUrl = logoUrl;

      const data = await createBrandMutation.mutateAsync(body);
      if (signal.aborted) return;

      const newBrand = {
        id: data.id,
        name: newBrandName.trim(),
        slug,
        logoUrl,
      };
      onChange?.(newBrand);

      // Reset modal — useCreateBrand already invalidates brandKeys.all in the
      // background; no need to await the refetch before closing.
      setNewBrandName('');
      setNewBrandDescription('');
      setNewBrandWebsite('');
      setBrandImagePreviewUrl('');
      setBrandImageName('');
      setBrandImageFile(null);
      setIsAddModalOpen(false);
    } catch (err) {
      if (signal.aborted || err?.name === 'AbortError') return;
      setCreateError(err.message);
    } finally {
      if (createAbortRef.current === controller) {
        createAbortRef.current = null;
      }
      setCreating(false);
    }
  }

  return (
    <div className={styles.brandSelect} ref={rootRef}>
      <button
        type="button"
        className={`${styles.brandSelectTrigger} ${hasError ? styles.fieldError : ''}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => {
          setOpen((current) => {
            if (!current) setSearchQuery('');
            return !current;
          });
        }}
      >
        <span className={styles.brandSelectValue}>
          {selectedBrand?.name ??
            (value && brandsLoading ? 'Загрузка...' : 'Бренд')}
        </span>
        <span className={styles.selectChevron}>
          <ChevronIcon />
        </span>
      </button>

      {open ? (
        <div
          className={styles.brandDropdown}
          role="listbox"
          aria-label="Список брендов"
        >
          <div className={styles.dropdownSearchWrap}>
            <input
              className={styles.dropdownSearchInput}
              placeholder="Поиск бренда..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setActiveIndex(-1);
              }}
              onKeyDown={handleDropdownKeyDown}
              autoFocus
              onMouseDown={(e) => e.stopPropagation()}
            />
          </div>
          <div className={styles.brandDropdownScrollArea}>
            {brandsLoading ? (
              <div className={styles.brandSectionHeader}>Загрузка…</div>
            ) : brandsLoadError ? (
              <div style={{ padding: '12px 16px', textAlign: 'center' }}>
                <p
                  style={{ margin: '0 0 8px', color: '#ef4444', fontSize: 13 }}
                >
                  Не удалось загрузить бренды
                </p>
                <button
                  type="button"
                  className={styles.brandAddButton}
                  onClick={() => refetchBrands()}
                  style={{ width: '100%' }}
                >
                  Повторить
                </button>
              </div>
            ) : filteredSections.length === 0 ? (
              <div className={styles.brandSectionHeader}>
                {searchQuery ? 'Ничего не найдено' : 'Нет брендов'}
              </div>
            ) : (
              filteredSections.map((section) => {
                // Track flat index for keyboard navigation
                let sectionStartIndex = 0;
                for (const s of filteredSections) {
                  if (s.key === section.key) break;
                  sectionStartIndex += s.brands.length;
                }
                return (
                  <section key={section.key} className={styles.brandSection}>
                    <div className={styles.brandSectionHeader}>
                      {section.key}
                    </div>
                    {section.brands.map((brand, brandIdx) => {
                      const isSelected = selectedBrand?.id === brand.id;
                      const flatIdx = sectionStartIndex + brandIdx;
                      const isActive = flatIdx === activeIndex;

                      return (
                        <button
                          key={brand.id}
                          type="button"
                          className={styles.brandOption}
                          role="option"
                          aria-selected={isSelected}
                          style={
                            isActive ? { background: '#f4f3f1' } : undefined
                          }
                          onClick={() => {
                            onChange?.(brand);
                            setOpen(false);
                          }}
                        >
                          <div className={styles.brandOptionMain}>
                            <BrandMark brand={brand} />
                            <span className={styles.brandOptionName}>
                              {brand.name}
                            </span>
                          </div>
                          <span
                            className={styles.brandOptionCheck}
                            aria-hidden="true"
                          >
                            {isSelected ? (
                              <span className={styles.brandOptionCheckInner} />
                            ) : null}
                          </span>
                        </button>
                      );
                    })}
                  </section>
                );
              })
            )}
          </div>

          <button
            type="button"
            className={styles.brandAddButton}
            onClick={openAddBrandModal}
          >
            <span className={styles.brandAddIcon}>
              <PlusIcon />
            </span>
            <span>Добавить бренд</span>
          </button>
        </div>
      ) : null}

      {isAddModalOpen ? (
        <div
          className={styles.brandModalOverlay}
          role="presentation"
          onClick={closeAddBrandModal}
        >
          <div
            ref={modalRef}
            className={styles.brandModal}
            role="dialog"
            aria-modal="true"
            aria-labelledby="brand-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className={styles.brandModalHeader}>
              <h3 id="brand-modal-title" className={styles.brandModalTitle}>
                Добавление бренда
              </h3>
              <button
                type="button"
                className={styles.brandModalClose}
                aria-label="Закрыть окно добавления бренда"
                onClick={closeAddBrandModal}
              >
                <CloseIcon />
              </button>
            </div>

            <div className={styles.brandModalBody}>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className={styles.brandModalFileInput}
                onChange={handleBrandImageChange}
              />

              <button
                type="button"
                className={
                  brandImagePreviewUrl
                    ? styles.brandModalUploadPreview
                    : styles.brandModalUpload
                }
                onClick={openFilePicker}
              >
                {brandImagePreviewUrl ? (
                  <>
                    <img
                      src={brandImagePreviewUrl}
                      alt={brandImageName || 'Загруженный логотип бренда'}
                      className={styles.brandModalPreviewImage}
                    />
                    <span className={styles.brandModalPreviewHint}>
                      Изменить изображение
                    </span>
                  </>
                ) : (
                  <>
                    <span className={styles.brandModalUploadIcon}>
                      <UploadIcon />
                    </span>
                    <span className={styles.brandModalUploadText}>
                      Загрузить изображение
                    </span>
                  </>
                )}
              </button>

              <input
                className={styles.brandModalInput}
                placeholder="Название бренда *"
                value={newBrandName}
                onChange={(event) => {
                  setNewBrandName(event.target.value);
                  setCreateError('');
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    handleCreateBrand();
                  }
                }}
              />

              {/* #20 — Extra optional fields */}
              <input
                className={styles.brandModalInput}
                placeholder="Описание бренда (необязательно)"
                value={newBrandDescription}
                onChange={(e) => setNewBrandDescription(e.target.value)}
              />
              <input
                className={styles.brandModalInput}
                placeholder="Сайт бренда (необязательно)"
                type="url"
                value={newBrandWebsite}
                onChange={(e) => setNewBrandWebsite(e.target.value)}
              />

              {createError && (
                <p
                  style={{
                    color: '#e53e3e',
                    fontSize: '13px',
                    margin: '4px 0 0',
                  }}
                >
                  {createError}
                </p>
              )}
            </div>

            <div className={styles.brandModalActions}>
              <button
                type="button"
                className={styles.brandModalPrimaryButton}
                disabled={!isBrandFormComplete || creating}
                onClick={handleCreateBrand}
              >
                {creating ? 'Создание...' : 'Добавить бренд'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
