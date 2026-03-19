'use client';

import { useState } from 'react';
import styles from './page.module.css';

const DELIVERY_OPTIONS = [
  { value: 'china', label: 'Из Китая' },
  { value: 'stock', label: 'Из наличия' },
];

function ArrowIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M5.8335 14H22.1668M22.1668 14L14.5835 6.41666M22.1668 14L14.5835 21.5833"
        stroke="black"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function DeliverySection() {
  const [deliveryMode, setDeliveryMode] = useState('china');
  const [urlValue, setUrlValue] = useState('');
  const [appliedUrl, setAppliedUrl] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);

  const showUrlAction = Boolean(urlValue.trim());

  function applyUrl() {
    const nextUrl = urlValue.trim();

    if (!nextUrl) {
      return;
    }

    if (!nextUrl.startsWith('https://') && !nextUrl.startsWith('http://')) {
      return;
    }

    setAppliedUrl(nextUrl);
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>Доставка</h2>
      <div className={styles.fieldGroup}>
        <div
          className={styles.segmented}
          role="tablist"
          aria-label="Способ доставки"
        >
          {DELIVERY_OPTIONS.map((option) => {
            const isActive = option.value === deliveryMode;

            return (
              <button
                key={option.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={isActive ? styles.segmentActive : styles.segment}
                onClick={() => setDeliveryMode(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        <div className={styles.sizeTableUrlRow}>
          <div
            className={
              urlFocused
                ? styles.sizeTableUrlFieldFocused
                : styles.sizeTableUrlField
            }
          >
            <span className={styles.sizeTableUrlLabel}>Ссылка на товар</span>
            <input
              value={urlValue}
              onChange={(event) => setUrlValue(event.target.value)}
              onFocus={() => setUrlFocused(true)}
              onBlur={() => setUrlFocused(false)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  applyUrl();
                }
              }}
              className={styles.sizeTableUrlInput}
              aria-label="Ссылка на товар"
            />
          </div>
          {showUrlAction ? (
            <button
              type="button"
              className={styles.sizeTableUrlAction}
              onClick={applyUrl}
              aria-label="Сохранить ссылку на товар"
            >
              <ArrowIcon />
            </button>
          ) : null}
        </div>

        <input type="hidden" value={appliedUrl} readOnly />
      </div>
    </section>
  );
}
