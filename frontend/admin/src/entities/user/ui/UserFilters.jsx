'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import styles from './styles/users.module.css';

function SearchInlineIcon(props) {
  return (
    <svg
      width="19"
      height="19"
      viewBox="0 0 19 19"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path
        d="M7.72559 0.958984C11.4623 0.95911 14.4912 3.98879 14.4912 7.72559C14.4911 11.4623 11.4623 14.4911 7.72559 14.4912C3.98879 14.4912 0.95911 11.4623 0.958984 7.72559C0.958984 3.98872 3.98872 0.958984 7.72559 0.958984Z"
        stroke="black"
        strokeWidth="1.91831"
      />
      <path
        d="M12.7061 12.875C12.7061 12.875 15.622 15.7391 17.4903 17.5743"
        stroke="black"
        strokeWidth="1.91831"
      />
    </svg>
  );
}

export function UserFilters({ roles, onFilterChange }) {
  const [search, setSearch] = useState('');
  const [roleId, setRoleId] = useState('');
  const [isActive, setIsActive] = useState('');
  const debounceRef = useRef(null);

  const emitChange = useCallback(
    (overrides = {}) => {
      const filters = {
        search,
        roleId,
        isActive,
        ...overrides,
      };
      onFilterChange(filters);
    },
    [search, roleId, isActive, onFilterChange],
  );

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    debounceRef.current = setTimeout(() => {
      emitChange();
    }, 400);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [search, emitChange]);

  function handleRoleChange(e) {
    const value = e.target.value;
    setRoleId(value);
    emitChange({ roleId: value });
  }

  function handleStatusChange(e) {
    const value = e.target.value;
    setIsActive(value);
    emitChange({ isActive: value });
  }

  function handleReset() {
    setSearch('');
    setRoleId('');
    setIsActive('');
    onFilterChange({ search: '', roleId: '', isActive: '' });
  }

  const showReset = Boolean(search.trim()) || roleId !== '' || isActive !== '';

  return (
    <div className={styles.filters}>
      <div className={styles.search}>
        <SearchInlineIcon className={styles.searchIcon} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск по email или имени"
          className={styles.searchInput}
          type="search"
          aria-label="Поиск пользователей"
        />
      </div>

      <select
        value={roleId}
        onChange={handleRoleChange}
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
        onChange={handleStatusChange}
        className={styles.filterSelect}
        aria-label="Фильтр по статусу"
      >
        <option value="">Все статусы</option>
        <option value="true">Активные</option>
        <option value="false">Неактивные</option>
      </select>

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
