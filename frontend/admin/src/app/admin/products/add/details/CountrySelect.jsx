'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchCountries } from '@/services/geo';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

/**
 * Searchable country selector for the supplier creation modal.
 *
 * Fetches countries from `/api/geo/countries?lang=ru` on first open,
 * then filters locally by search query.
 *
 * Props:
 *   value    – selected country alpha-2 code (e.g. "RU")
 *   onChange – (code: string) => void
 */
export default function CountrySelect({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef(null);
  const searchRef = useRef(null);
  const loadedRef = useRef(false);
  const loadingRef = useRef(false);

  const selectedItem = items.find((i) => i.code === value);
  const displayLabel = selectedItem ? selectedItem.name : '';

  // Local filter — countries are loaded once, then filtered on client
  const filtered = search
    ? items.filter((i) =>
        i.name.toLowerCase().includes(search.toLowerCase()) ||
        i.code.toLowerCase().includes(search.toLowerCase()),
      )
    : items;

  const loadCountries = useCallback(async (force = false) => {
    if (!force && (loadedRef.current || loadingRef.current)) return;
    loadingRef.current = true;
    setLoading(true);
    setError(false);
    try {
      const data = await fetchCountries();
      setItems(data.items);
      loadedRef.current = true;
      setLoaded(true);
    } catch {
      setError(true);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, []);

  function handleToggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    setSearch('');
    setActiveIndex(-1);
    loadCountries();
    setTimeout(() => searchRef.current?.focus(), 50);
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

  function handleSelect(code) {
    onChange?.(code);
    setOpen(false);
    setSearch('');
    setActiveIndex(-1);
  }

  return (
    <div className={styles.countrySelect} ref={containerRef}>
      <button
        type="button"
        className={styles.countryTrigger}
        onClick={handleToggle}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={value ? styles.countryValue : styles.countryPlaceholder}>
          {value ? displayLabel : 'Страна'}
        </span>
        <span className={styles.countryChevron}>
          <ChevronIcon />
        </span>
      </button>

      {open && (
        <div className={styles.countryDropdown} role="listbox" aria-label="Список стран">
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
                  onClick={() => loadCountries(true)}
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
                    <span className={styles.countryOptionName}>{item.name}</span>
                    <span className={styles.countryOptionCode}>{item.code}</span>
                    {isSelected && <span className={styles.countryCheck}>✓</span>}
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
