'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { useOutsideClick } from '@/shared/hooks/useOutsideClick';

import { STAFF_SORT_OPTIONS } from '../api/staff';
import styles from './styles/staff.module.css';

const DEFAULT_SORT = 'created_at:desc';

export function StaffFilters({ value, roles = [], onFilterChange }) {
  const [search, setSearch] = useState(value?.search ?? '');
  const [roleId, setRoleId] = useState(value?.roleId ?? '');
  const [isActive, setIsActive] = useState(value?.isActive ?? '');
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
      // Cancel the search debounce — otherwise a synchronous role/status
      // change here would also trigger the pending search timer right
      // after, firing two near-identical onFilterChange calls back to back.
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      onFilterChange({ search, roleId, isActive, sort, ...overrides });
    },
    [search, roleId, isActive, sort, onFilterChange],
  );

  // Debounce only the search-text path; selects emit synchronously through
  // their handlers. Watching `[search, emit]` would re-run the timer on every
  // role/status/sort change too — and `emit` itself rebuilds whenever any
  // filter changes, so a 400 ms phantom call would land on top of the
  // synchronous one. Skip the very first run after mount: the parent already
  // owns the initial `value`, so we don't need to echo it back.
  const initialSearchRef = useRef(search);
  useEffect(() => {
    if (search === initialSearchRef.current) return undefined;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onFilterChange({ search, roleId, isActive, sort });
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // We intentionally only depend on `search`. `roleId`/`isActive`/`sort` are
    // captured by closure and read at fire time — they never need to *trigger*
    // the timer, only flow through when search does.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  function handleRole(e) {
    setRoleId(e.target.value);
    emit({ roleId: e.target.value });
  }
  function handleStatus(e) {
    setIsActive(e.target.value);
    emit({ isActive: e.target.value });
  }
  function handleSort(nextSort) {
    setSort(nextSort);
    setSortOpen(false);
    emit({ sort: nextSort });
  }
  function handleReset() {
    setSearch('');
    setRoleId('');
    setIsActive('');
    setSort(DEFAULT_SORT);
    onFilterChange({
      search: '',
      roleId: '',
      isActive: '',
      sort: DEFAULT_SORT,
    });
  }

  const sortLabel =
    STAFF_SORT_OPTIONS.find((o) => o.value === sort)?.label ??
    STAFF_SORT_OPTIONS[0].label;
  const showReset =
    Boolean(search.trim()) ||
    roleId !== '' ||
    isActive !== '' ||
    sort !== DEFAULT_SORT;

  return (
    <div className={styles.filters}>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Поиск сотрудника по email или имени"
        className={styles.searchInput}
        type="search"
        aria-label="Поиск сотрудников"
      />

      <select
        value={roleId}
        onChange={handleRole}
        className={styles.filterSelect}
        aria-label="Фильтр по роли"
      >
        <option value="">Все роли</option>
        {roles.map((role) => (
          <option key={role.id} value={role.id}>
            {role.name}
          </option>
        ))}
      </select>

      <select
        value={isActive}
        onChange={handleStatus}
        className={styles.filterSelect}
        aria-label="Фильтр по статусу"
      >
        <option value="">Все статусы</option>
        <option value="true">Активные</option>
        <option value="false">Неактивные</option>
      </select>

      <div className={styles.sortWrap} ref={sortRef}>
        <button
          type="button"
          className={styles.sortButton}
          onClick={() => setSortOpen((v) => !v)}
          aria-haspopup="listbox"
          aria-expanded={sortOpen}
        >
          {sortLabel}
          <span aria-hidden="true">▾</span>
        </button>
        {sortOpen && (
          <ul
            className={styles.sortMenu}
            role="listbox"
            aria-label="Сортировка сотрудников"
          >
            {STAFF_SORT_OPTIONS.map((option) => (
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
        >
          Сбросить
        </button>
      )}
    </div>
  );
}
