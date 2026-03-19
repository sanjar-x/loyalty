'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import ChevronIcon from '@/assets/icons/chevron.svg';
import SearchIcon from '@/assets/icons/search.svg';
import { useOutsideClick } from '@/hooks/useOutsideClick';
import styles from './products.module.css';

export function DropdownPill({
  label,
  value,
  displayValue,
  active,
  options,
  onChange,
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const rootRef = useRef(null);
  useOutsideClick({ open, onClose: () => setOpen(false), ref: rootRef });

  const searchable = Boolean(options?.some((o) => o.searchable));
  const groupByInitial = Boolean(options?.some((o) => o.groupByInitial));
  const isActive = typeof active === 'boolean' ? active : value !== 'all';

  useEffect(() => {
    if (!open) setSearch('');
  }, [open]);

  const normalizedQuery = search.trim().toLowerCase();
  const allOption = options?.find((o) => o.value === 'all') ?? null;

  const restOptions = useMemo(
    () => (options ?? []).filter((o) => o.value !== 'all'),
    [options],
  );

  const filteredRest = useMemo(() => {
    if (!normalizedQuery) return restOptions;
    return restOptions.filter((o) =>
      String(o.label ?? '')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [normalizedQuery, restOptions]);

  const grouped = useMemo(() => {
    if (!groupByInitial) return [{ key: null, items: filteredRest }];
    const buckets = new Map();
    filteredRest.forEach((o) => {
      const first = String(o.label ?? '')
        .trim()
        .charAt(0)
        .toUpperCase();
      const key = first || '#';
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(o);
    });
    const keys = Array.from(buckets.keys()).sort((a, b) =>
      a.localeCompare(b, 'ru-RU'),
    );
    return keys.map((key) => ({
      key,
      items: buckets
        .get(key)
        .slice()
        .sort((a, b) =>
          String(a.label).localeCompare(String(b.label), 'ru-RU'),
        ),
    }));
  }, [filteredRest, groupByInitial]);

  return (
    <div className={styles.dropdownRoot} ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          styles.dropdownButton,
          isActive && styles.dropdownButtonActive,
        )}
      >
        <span className={styles.dropdownLabel}>{label}</span>
        {displayValue ? (
          <span className={styles.dropdownValue}>{displayValue}</span>
        ) : null}
        <ChevronIcon
          className={cn(styles.chevron, open && styles.chevronOpen)}
        />
      </button>

      {open && (
        <div className={styles.menu}>
          {searchable && (
            <div className={styles.menuHeader}>
              <div className={styles.menuSearch}>
                <SearchIcon className={styles.menuSearchIcon} />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Найти бренд"
                  className={styles.menuSearchInput}
                />
              </div>
            </div>
          )}

          <div className={styles.menuScroll}>
            {allOption && (
              <button
                key={allOption.value}
                type="button"
                onClick={() => {
                  onChange(allOption.value);
                  setOpen(false);
                }}
                className={styles.menuItem}
              >
                <span className={styles.menuItemLabel}>{allOption.label}</span>
                <span className={styles.menuItemRight}>
                  {typeof allOption.count === 'number' ? (
                    <span className={styles.menuItemCount}>
                      {allOption.count.toLocaleString('ru-RU')}
                    </span>
                  ) : null}
                  <span
                    className={cn(
                      styles.menuCheck,
                      allOption.value === value && styles.menuCheckVisible,
                    )}
                  >
                    ✓
                  </span>
                </span>
              </button>
            )}

            {grouped.map((section) => (
              <div key={section.key ?? 'all'} className={styles.menuSection}>
                {section.key ? (
                  <div className={styles.menuSectionLabel}>{section.key}</div>
                ) : null}

                {section.items.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setOpen(false);
                    }}
                    className={styles.menuItem}
                  >
                    <span className={styles.menuItemLabel}>{opt.label}</span>
                    <span className={styles.menuItemRight}>
                      {typeof opt.count === 'number' ? (
                        <span className={styles.menuItemCount}>
                          {opt.count.toLocaleString('ru-RU')}
                        </span>
                      ) : null}
                      <span
                        className={cn(
                          styles.menuCheck,
                          opt.value === value && styles.menuCheckVisible,
                        )}
                      >
                        ✓
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
