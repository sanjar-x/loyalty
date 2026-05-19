'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useCountries } from '@/shared/api/geo';
import { ChevronIcon } from './icons';
import styles from './styles/productForm.module.css';

/**
 * Searchable country selector for the supplier creation modal.
 *
 * Pulls the country catalogue via TanStack Query (cached for 30 minutes
 * across the whole admin), then filters locally by search query.
 */
export default function CountrySelect({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef(null);
  const searchRef = useRef(null);

  const {
    data: countriesData,
    isPending: initialLoading,
    isError: error,
    refetch,
  } = useCountries();
  const items = useMemo(() => countriesData?.items ?? [], [countriesData]);
  // Don't flash a loader on background refetches; only on the very first load.
  const loading = initialLoading && !countriesData;

  const selectedItem = items.find((i) => i.code === value);
  const displayLabel = selectedItem ? selectedItem.name : '';

  // Local filter — countries are cached once, then filtered on the client.
  const filtered = search
    ? items.filter((i) => {
        const q = search.toLowerCase();
        return (
          i.name.toLowerCase().includes(q) || i.code.toLowerCase().includes(q)
        );
      })
    : items;

  function handleToggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    setSearch('');
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
      }
    }
    function handleEscape(e) {
      if (e.key === 'Escape') {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div className={styles.countrySelect} ref={containerRef}>
      <button
        type="button"
        className={styles.countryTrigger}
        onClick={handleToggle}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span
          className={value ? styles.countryValue : styles.countryPlaceholder}
        >
          {value ? displayLabel : 'Страна'}
        </span>
        <span className={styles.countryChevron}>
          <ChevronIcon />
        </span>
      </button>

      {open && (
        <div
          className={styles.countryDropdown}
          role="listbox"
          aria-label="Список стран"
        >
          <div className={styles.countrySearchWrap}>
            <input
              ref={searchRef}
              className={styles.countrySearchInput}
              placeholder="Поиск страны..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setActiveIndex(-1);
              }}
              onKeyDown={handleSearchKeyDown}
            />
          </div>

          <div className={styles.countryScrollArea}>
            {loading ? (
              <div className={styles.countryHint}>Загрузка…</div>
            ) : error ? (
              <div className={styles.countryHint}>
                <span style={{ color: '#ef4444' }}>Ошибка загрузки</span>
                <button
                  type="button"
                  className={styles.countryRetry}
                  onClick={() => refetch()}
                >
                  Повторить
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <div className={styles.countryHint}>
                {search ? 'Ничего не найдено' : 'Нет стран'}
              </div>
            ) : (
              filtered.map((item, idx) => {
                const isSelected = item.code === value;
                const isActive = idx === activeIndex;
                return (
                  <button
                    key={item.code}
                    type="button"
                    className={styles.countryOption}
                    role="option"
                    aria-selected={isSelected}
                    style={isActive ? { background: '#f4f3f1' } : undefined}
                    onClick={() => handleSelect(item.code)}
                  >
                    <span className={styles.countryOptionName}>
                      {item.name}
                    </span>
                    <span className={styles.countryOptionCode}>
                      {item.code}
                    </span>
                    {isSelected && (
                      <span className={styles.countryCheck}>✓</span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
