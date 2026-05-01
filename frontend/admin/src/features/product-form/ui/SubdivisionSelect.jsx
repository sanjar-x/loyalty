'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSubdivisions } from '@/shared/api/geo';
import { ChevronIcon } from './icons';
import styles from './styles/productForm.module.css';

/**
 * Searchable subdivision (region) selector.
 *
 * Pulls the subdivision list for the given country via TanStack Query
 * (cached per country code). Search filtering is done locally to avoid
 * thrashing the cache on every keystroke.
 */
export default function SubdivisionSelect({ countryCode, value, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef(null);
  const searchRef = useRef(null);

  const {
    data: subdivisionsData,
    isPending: initialLoading,
    isFetching,
    isError: error,
    refetch,
  } = useSubdivisions(countryCode);

  const items = useMemo(
    () => subdivisionsData?.items ?? [],
    [subdivisionsData],
  );
  // Spinner only on the first load (or first time we see a given country).
  const loading = initialLoading && !subdivisionsData;
  // Only render the "no regions" hint after the request has settled —
  // otherwise we'd flash it while switching countries when the previous
  // country's response is still cached.
  const notFound = Boolean(subdivisionsData?.notFound) && !isFetching;

  const selectedItem = items.find((i) => i.code === value);
  const displayLabel = selectedItem
    ? `${selectedItem.name} (${selectedItem.code})`
    : value || '';

  const filtered = search
    ? items.filter((i) => {
        const q = search.toLowerCase();
        return (
          i.name.toLowerCase().includes(q) || i.code.toLowerCase().includes(q)
        );
      })
    : items;

  // Reset transient UI state when the parent country switches.
  useEffect(() => {
    setSearch('');
    setActiveIndex(-1);
  }, [countryCode]);

  function handleToggle() {
    if (!countryCode) return;
    if (open) {
      setOpen(false);
      setSearch('');
      return;
    }
    setOpen(true);
    setActiveIndex(-1);
    setTimeout(() => searchRef.current?.focus(), 50);
  }

  function handleSelect(code) {
    onChange?.(code);
    setOpen(false);
    setSearch('');
    setActiveIndex(-1);
  }

  function handleSearchKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < filtered.length) {
        handleSelect(filtered[activeIndex].code);
      }
    }
  }

  // Close on outside click / escape
  useEffect(() => {
    if (!open) return;
    function handlePointerDown(e) {
      if (!containerRef.current?.contains(e.target)) {
        setOpen(false);
        setSearch('');
      }
    }
    function handleEscape(e) {
      if (e.key === 'Escape') {
        setOpen(false);
        setSearch('');
      }
    }
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  function handleClear(e) {
    e.stopPropagation();
    onChange?.('');
  }

  const disabled = !countryCode;

  return (
    <div className={styles.subdivisionSelect} ref={containerRef}>
      <button
        type="button"
        className={styles.subdivisionTrigger}
        onClick={handleToggle}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span
          className={
            value ? styles.subdivisionValue : styles.subdivisionPlaceholder
          }
        >
          {value ? displayLabel : 'Регион — необязательно'}
        </span>
        <span className={styles.subdivisionActions}>
          {value && (
            <span
              role="button"
              tabIndex={-1}
              className={styles.subdivisionClear}
              onClick={handleClear}
              aria-label="Очистить регион"
            >
              ×
            </span>
          )}
          <span className={styles.subdivisionChevron}>
            <ChevronIcon />
          </span>
        </span>
      </button>

      {open && (
        <div
          className={styles.subdivisionDropdown}
          role="listbox"
          aria-label="Список регионов"
        >
          {notFound ? (
            <div className={styles.subdivisionHint}>
              Для этой страны регионы пока не добавлены
            </div>
          ) : (
            <>
              <div className={styles.subdivisionSearchWrap}>
                <input
                  ref={searchRef}
                  className={styles.subdivisionSearchInput}
                  placeholder="Поиск региона..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setActiveIndex(-1);
                  }}
                  onKeyDown={handleSearchKeyDown}
                />
              </div>

              <div className={styles.subdivisionScrollArea}>
                {loading ? (
                  <div className={styles.subdivisionHint}>Загрузка…</div>
                ) : error ? (
                  <div className={styles.subdivisionHint}>
                    <span style={{ color: '#ef4444' }}>Ошибка загрузки</span>
                    <button
                      type="button"
                      className={styles.subdivisionRetry}
                      onClick={() => refetch()}
                    >
                      Повторить
                    </button>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className={styles.subdivisionHint}>
                    {search ? 'Ничего не найдено' : 'Нет регионов'}
                  </div>
                ) : (
                  filtered.map((item, idx) => {
                    const isSelected = item.code === value;
                    const isActive = idx === activeIndex;
                    return (
                      <button
                        key={item.code}
                        type="button"
                        className={styles.subdivisionOption}
                        role="option"
                        aria-selected={isSelected}
                        style={isActive ? { background: '#f4f3f1' } : undefined}
                        onClick={() => handleSelect(item.code)}
                      >
                        <span className={styles.subdivisionOptionName}>
                          {item.name}
                        </span>
                        <span className={styles.subdivisionOptionCode}>
                          {item.code}
                        </span>
                        {isSelected && (
                          <span className={styles.subdivisionCheck}>✓</span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
