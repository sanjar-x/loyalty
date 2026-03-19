'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

const BRAND_SECTIONS = [
  {
    key: 'A',
    brands: [
      { id: 'adidas', name: 'Adidas', mark: 'adidas' },
      { id: 'armani', name: 'Armani', mark: 'ARMANI' },
    ],
  },
  {
    key: 'B',
    brands: [
      { id: 'balenciaga', name: 'BALENCIAGA', mark: 'BALENCIAGA' },
      { id: 'burberry', name: 'Burberry', mark: 'BURBERRY' },
    ],
  },
];

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
  return (
    <div className={styles.brandOptionLogo} aria-hidden="true">
      <span className={styles.brandOptionLogoText}>{brand.mark}</span>
    </div>
  );
}

export default function BrandSelect() {
  const [open, setOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [brandImagePreviewUrl, setBrandImagePreviewUrl] = useState('');
  const [brandImageName, setBrandImageName] = useState('');
  const [newBrandName, setNewBrandName] = useState('');
  const [newBrandCategory, setNewBrandCategory] = useState('');
  const fileInputRef = useRef(null);
  const rootRef = useRef(null);

  const isBrandFormComplete = Boolean(
    brandImagePreviewUrl && newBrandName.trim() && newBrandCategory,
  );

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

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function openAddBrandModal() {
    setOpen(false);
    setIsAddModalOpen(true);
  }

  function closeAddBrandModal() {
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
    event.target.value = '';
  }

  return (
    <div className={styles.brandSelect} ref={rootRef}>
      <button
        type="button"
        className={styles.brandSelectTrigger}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span className={styles.brandSelectValue}>
          {selectedBrand?.name ?? 'Бренд'}
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
          <div className={styles.brandDropdownScrollArea}>
            {BRAND_SECTIONS.map((section) => (
              <section key={section.key} className={styles.brandSection}>
                <div className={styles.brandSectionHeader}>{section.key}</div>
                {section.brands.map((brand) => {
                  const isSelected = selectedBrand?.id === brand.id;

                  return (
                    <button
                      key={brand.id}
                      type="button"
                      className={styles.brandOption}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => {
                        setSelectedBrand(brand);
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
            ))}
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
                      <svg
                        width="12"
                        height="24"
                        viewBox="0 0 12 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                        aria-hidden="true"
                      >
                        <path
                          d="M10.3636 5.45455V18C10.3636 20.4109 8.41091 22.3636 6 22.3636C3.58909 22.3636 1.63636 20.4109 1.63636 18V4.36364C1.63636 2.85818 2.85818 1.63636 4.36364 1.63636C5.86909 1.63636 7.09091 2.85818 7.09091 4.36364V15.8182C7.09091 16.4182 6.60545 16.9091 6 16.9091C5.39455 16.9091 4.90909 16.4182 4.90909 15.8182V5.45455H3.27273V15.8182C3.27273 17.3236 4.49455 18.5455 6 18.5455C7.50545 18.5455 8.72727 17.3236 8.72727 15.8182V4.36364C8.72727 1.95273 6.77455 0 4.36364 0C1.95273 0 0 1.95273 0 4.36364V18C0 21.3164 2.68909 24 6 24C9.31091 24 12 21.3164 12 18V5.45455H10.3636Z"
                          fill="black"
                        />
                      </svg>
                    </span>
                    <span className={styles.brandModalUploadText}>
                      Загрузить изображение
                    </span>
                  </>
                )}
              </button>

              <input
                className={styles.brandModalInput}
                placeholder="Название"
                value={newBrandName}
                onChange={(event) => setNewBrandName(event.target.value)}
              />

              <div className={styles.brandModalSelectWrapper}>
                <select
                  value={newBrandCategory}
                  className={styles.brandModalSelect}
                  onChange={(event) => setNewBrandCategory(event.target.value)}
                >
                  <option value="" disabled>
                    Категория
                  </option>
                  <option value="clothes">Одежда</option>
                  <option value="shoes">Обувь</option>
                  <option value="accessories">Аксессуары</option>
                </select>
                <span className={styles.brandModalSelectChevron}>
                  <ChevronIcon />
                </span>
              </div>
            </div>

            <div className={styles.brandModalActions}>
              <button
                type="button"
                className={styles.brandModalPrimaryButton}
                disabled={!isBrandFormComplete}
              >
                Добавить бренд
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
