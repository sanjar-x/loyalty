'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

import SortIcon from '@/assets/icons/sort.svg';

import { useOutsideClick } from '@/shared/hooks/useOutsideClick';

import { CUSTOMER_SORT_OPTIONS } from '../api/customers';
import styles from './styles/users.module.css';

const DEFAULT_SORT = 'created_at:desc';

function SearchInlineIcon(props) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 19 19"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path
        d="M7.72559 0.958984C11.4623 0.95911 14.4912 3.98879 14.4912 7.72559C14.4911 11.4623 11.4623 14.4911 7.72559 14.4912C3.98879 14.4912 0.95911 11.4623 0.958984 7.72559C0.958984 3.98872 3.98872 0.958984 7.72559 0.958984Z"
        stroke="#7e7e7e"
        strokeWidth="1.91831"
      />
      <path
        d="M12.7061 12.875C12.7061 12.875 15.622 15.7391 17.4903 17.5743"
        stroke="#7e7e7e"
        strokeWidth="1.91831"
      />
    </svg>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg
      width="10"
      height="6"
      viewBox="0 0 10 6"
      fill="none"
      style={{
        transform: open ? 'rotate(180deg)' : 'none',
        transition: 'transform 150ms',
      }}
      aria-hidden="true"
    >
      <path
        d="M1 1L5 5L9 1"
        stroke="#22252b"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// `/admin/customers` doesn't accept a `role_id` filter — every customer carries
// the `customer` role implicitly — so this component intentionally omits it.
export function UserFilters({ value, onFilterChange }) {
  const [search, setSearch] = useState(value?.search ?? '');
  const [sort, setSort] = useState(value?.sort ?? DEFAULT_SORT);
  const [sortOpen, setSortOpen] = useState(false);
  const debounceRef = useRef(null);
  const sortRef = useRef(null);

  useOutsideClick({
    open: sortOpen,
    onClose: () => setSortOpen(false),
    ref: sortRef,
  });

  const emit = useCallback(
    (overrides = {}) => {
      onFilterChange({ search, sort, ...overrides });
    },
    [search, sort, onFilterChange],
  );

  // Debounce search-term changes so we don't hammer the backend.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      emit();
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search, emit]);

  function handleSort(nextSort) {
    setSort(nextSort);
    setSortOpen(false);
    emit({ sort: nextSort });
  }

  function handleReset() {
    setSearch('');
    setSort(DEFAULT_SORT);
    onFilterChange({ search: '', sort: DEFAULT_SORT });
  }

  const sortLabel =
    CUSTOMER_SORT_OPTIONS.find((opt) => opt.value === sort)?.label ??
    CUSTOMER_SORT_OPTIONS[0].label;

  const showReset = Boolean(search.trim()) || sort !== DEFAULT_SORT;

  return (
    <div className={styles.filters}>
      <div className={styles.search}>
        <SearchInlineIcon className={styles.searchIcon} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск пользователя"
          className={styles.searchInput}
          type="search"
          aria-label="Поиск пользователей"
        />
      </div>

      <div className={styles.sortWrap} ref={sortRef}>
        <button
          type="button"
          className={styles.sortButton}
          onClick={() => setSortOpen((v) => !v)}
          aria-haspopup="listbox"
          aria-expanded={sortOpen}
        >
          <SortIcon className={styles.sortIcon} width={16} height={16} />
          <span>{sortLabel}</span>
          <ChevronIcon open={sortOpen} />
        </button>

        {sortOpen && (
          <ul
            className={styles.sortMenu}
            role="listbox"
            aria-label="Сортировка пользователей"
          >
            {CUSTOMER_SORT_OPTIONS.map((option) => (
              <li key={option.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={sort === option.value}
                  className={`${styles.sortMenuItem} ${
                    sort === option.value ? styles.sortMenuItemActive : ''
                  }`}
                  onClick={() => handleSort(option.value)}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {showReset && (
        <button
          type="button"
          className={styles.resetButton}
          onClick={handleReset}
          aria-label="Сбросить фильтры"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 15 15"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M1 1L7.5 7.5M14 14L7.5 7.5M7.5 7.5L13.5357 1M7.5 7.5L1 14"
              stroke="#2D2D2D"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
