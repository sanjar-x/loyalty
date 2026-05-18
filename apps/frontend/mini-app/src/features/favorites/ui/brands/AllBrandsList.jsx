'use client';
import React, { useMemo, useState } from 'react';
import styles from './AllBrandsList.module.css';
import { cn as cx } from '@/shared/lib/ui-utils';

function getInitial(name) {
  const trimmed = typeof name === 'string' ? name.trim() : '';
  if (!trimmed) return '?';
  return trimmed.charAt(0).toUpperCase();
}

function getLetter(name) {
  const raw = typeof name === 'string' ? name.trim() : '';
  const first = raw ? raw[0] : '';
  return first ? first.toUpperCase() : '#';
}

function ImgWithFallback({ src, fallbacks, alt, className, onAllFailed }) {
  const sources = useMemo(
    () =>
      [src, ...(Array.isArray(fallbacks) ? fallbacks : [])].filter(
        (s) => typeof s === 'string' && s.trim()
      ),
    [src, fallbacks]
  );
  const [idx, setIdx] = useState(0);
  const [allFailed, setAllFailed] = useState(false);
  const current = sources[idx];

  if (!current || allFailed) return null;

  return (
    <img
      src={current}
      alt={alt}
      className={className}
      onError={() => {
        if (idx < sources.length - 1) {
          setIdx(idx + 1);
        } else {
          setAllFailed(true);
          onAllFailed?.();
        }
      }}
    />
  );
}

function BrandRow({ brand, onToggleFavorite }) {
  const [imageFailed, setImageFailed] = useState(false);
  const hasImage = Boolean(brand.image) && !imageFailed && !!String(brand.image).trim();

  return (
    <li className={cx(styles.c2, styles.tw2)}>
      <div className={cx(styles.c3, styles.tw3)}>
        <div className={cx(styles.c4, styles.tw4)}>
          {hasImage ? (
            <ImgWithFallback
              src={brand.image}
              fallbacks={brand.imageFallbacks}
              alt={brand.name}
              className={styles.c5}
              onAllFailed={() => setImageFailed(true)}
            />
          ) : (
            <span className={styles.fallbackInitial} aria-hidden="true">
              {getInitial(brand.name)}
            </span>
          )}
        </div>

        <div className={cx(styles.c6, styles.tw5)}>
          <span className={styles.c7}>{brand.name}</span>
          <span className={styles.c8}>Бренд</span>
        </div>
      </div>

      {onToggleFavorite ? (
        <button
          type="button"
          onClick={() => onToggleFavorite(brand.id)}
          className={cx(styles.c9, styles.tw6)}
          aria-pressed={brand.isFavorite}
          aria-label={brand.isFavorite ? 'Удалить из избранного' : 'Добавить в избранное'}
        >
          <img
            src={
              brand.isFavorite
                ? '/icons/global/active-heart.svg'
                : '/icons/global/not-active-heart.svg'
            }
            alt=""
            aria-hidden="true"
            className={styles.c10}
          />
        </button>
      ) : null}
    </li>
  );
}

export default function AllBrandsList({ brands, onToggleFavorite }) {
  const sorted = Array.isArray(brands)
    ? [...brands].sort((a, b) => String(a?.name || '').localeCompare(String(b?.name || '')))
    : [];

  return (
    <ul className={cx(styles.c1, styles.tw1)}>
      {sorted.map((brand, index) => {
        const letter = getLetter(brand?.name);
        const prev = index > 0 ? sorted[index - 1] : null;
        const prevLetter = prev ? getLetter(prev?.name) : null;
        const showLetter = letter !== prevLetter;

        return (
          <React.Fragment key={brand.id}>
            {showLetter ? (
              <li className={styles.letterRow} aria-hidden="true">
                {letter}
              </li>
            ) : null}
            <BrandRow brand={brand} onToggleFavorite={onToggleFavorite} />
          </React.Fragment>
        );
      })}
    </ul>
  );
}
