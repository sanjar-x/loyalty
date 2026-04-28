'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSubdivisions } from '@/services/geo';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

/**
 * Searchable subdivision (region) selector.
 *
 * Fetches subdivisions from `/api/v1/geo/countries/{countryCode}/subdivisions`
 * with debounced search. Renders inside the supplier creation modal.
 *
 * Props:
 *   countryCode – ISO alpha-2 (e.g. "RU", "CN"); empty = disabled
 *   value       – selected subdivision code (e.g. "RU-MOW")
 *   onChange     – (code: string) => void
 */
export default function SubdivisionSelect({ countryCode, value, onChange }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef(null);
  const searchRef = useRef(null);
  const debounceRef = useRef(null);

  // The currently selected item label
  const selectedItem = items.find((i) => i.code === value);
  const displayLabel = selectedItem ? `${selectedItem.name} (${selectedItem.code})` : value || '';

  // Reset when country changes
  useEffect(() => {
    setItems([]);
    setLoaded(false);
    setSearch('');
    setError(false);
    setNotFound(false);
    setActiveIndex(-1);
  }, [countryCode]);

  const loadSubdivisions = useCallback(
    async (searchQuery = '') => {
      if (!countryCode) return;
      setLoading(true);
      setError(false);
      try {
        const data = await fetchSubdivisions(countryCode, {
          search: searchQuery,
          limit: 50,
        });
        setItems(data.items);
        setNotFound(!!data.notFound);
        setLoaded(true);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    },
    [countryCode],
  );

  // Debounced search
  const handleSearchChange = useCallback(
    (e) => {
      const q = e.target.value;
      setSearch(q);
      setActiveIndex(-1);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        loadSubdivisions(q.trim());
      }, 300);
    },
    [loadSubdivisions],
  );

  function handleToggle() {
    if (!countryCode) return;
    if (open) {
      setOpen(false);
      setSearch('');
      return;
    }
    setOpen(true);
    setActiveIndex(-1);
    if (!loaded) loadSubdivisions('');
    setTimeout(() => searchRef.current?.focus(), 50);
  }

  function handleSearchKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < items.length) {
        handleSelect(items[activeIndex].code);
      }
    }
  }

  // Close on outside click
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

  // Cleanup debounce timer
  useEffect(() => () => clearTimeout(debounceRef.current), []);

  function handleSelect(code) {
    onChange?.(code);
    setOpen(false);
    setSearch('');
    setActiveIndex(-1);
  }

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
        <span className={value ? styles.subdivisionValue : styles.subdivisionPlaceholder}>
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
        <div className={styles.subdivisionDropdown} role="listbox" aria-label="Список регионов">
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
                  onChange={handleSearchChange}
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
                      onClick={() => loadSubdivisions(search.trim())}
                    >
                      Повторить
                    </button>
                  </div>
                ) : items.length === 0 ? (
                  <div className={styles.subdivisionHint}>
                    {search ? 'Ничего не найдено' : 'Нет регионов'}
                  </div>
                ) : (
                  items.map((item, idx) => {
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
                        <span className={styles.subdivisionOptionName}>{item.name}</span>
                        <span className={styles.subdivisionOptionCode}>{item.code}</span>
                        {isSelected && <span className={styles.subdivisionCheck}>✓</span>}
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
