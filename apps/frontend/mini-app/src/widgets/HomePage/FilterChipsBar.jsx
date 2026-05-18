import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/**
 * Home page filter-chip bar (sort / filters / category / type / brand /
 * price / original / delivery). Audit #1: ~210-line JSX split out of the
 * `app/page.jsx` god component — pure presentation.
 *
 * The page renders it when `showResults && !showOverlay`. Behavior comes
 * in via three callbacks: `onOpenSheet(name)` / `onClearFilter(name)` /
 * `onToggleOriginal()`.
 */

/* ── Chevron SVG ── */
function ChevDown() {
  return (
    <span className={styles.chev} aria-hidden="true">
      <svg
        width="11"
        height="12.57"
        viewBox="0 0 9 5"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M0.237441 0.240947C0.421218 0.0530257 0.719178 0.0530257 0.902954 0.240947L4.09961 3.50971L7.29626 0.240947C7.48004 0.0530257 7.778 0.0530257 7.96178 0.240947C8.14555 0.428869 8.14555 0.73355 7.96178 0.921471L4.43236 4.53049C4.24859 4.71842 3.95063 4.71842 3.76685 4.53049L0.237441 0.921471C0.0536653 0.73355 0.0536653 0.428869 0.237441 0.240947Z"
          fill="#7E7E7E"
        />
      </svg>
    </span>
  );
}

export default function FilterChipsBar({
  isFiltersBarHidden,
  sort,
  activeFilterCount,
  activeCategoryId,
  categoryChipLabel,
  typeIds,
  typeChipLabel,
  brandIds,
  brandChipLabel,
  priceRange,
  priceLabel,
  isOriginalOnly,
  hasDeliveryFilter,
  deliveryChipLabel,
  onOpenSheet,
  onClearFilter,
  onToggleOriginal,
}) {
  return (
    <div
      className={cn(styles.filtersBarInner, isFiltersBarHidden ? styles.filtersBarHidden : null)}
      aria-label="Фильтры"
    >
      <div className={cn(styles.filtersRow, 'scrollbar-hide')}>
        {/* Sort icon */}
        <button
          type="button"
          className={cn(styles.iconChip, sort !== 'popular' ? styles.iconChipActive : null)}
          aria-label="Сортировка"
          onClick={() => onOpenSheet('sort')}
        >
          <svg
            width="14"
            height="11"
            viewBox="0 0 14 11"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M6.94122 9.58731H0.766235M13.1162 5.17661H0.766235M13.1162 0.7659H0.766235"
              stroke={sort !== 'popular' ? 'white' : 'black'}
              strokeWidth="1.53178"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
        {/* Filters icon */}
        <button
          type="button"
          className={cn(styles.iconChip, activeFilterCount > 0 ? styles.iconChipActive : null)}
          aria-label="Фильтры"
          onClick={() => onOpenSheet('filters')}
        >
          <svg
            width="17"
            height="11"
            viewBox="0 0 17 11"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.1113 7.97225H16.1002M0.700195 7.97225H2.41131M2.41131 7.97225C2.41131 9.15352 3.36892 10.1111 4.5502 10.1111C5.73148 10.1111 6.68909 9.15352 6.68909 7.97225C6.68909 6.79097 5.73148 5.83335 4.5502 5.83335C3.36892 5.83335 2.41131 6.79097 2.41131 7.97225ZM15.2447 2.8389H16.1002M0.700195 2.8389H6.68909M12.2502 4.9778C11.0689 4.9778 10.1113 4.02018 10.1113 2.8389C10.1113 1.65763 11.0689 0.700012 12.2502 0.700012C13.4315 0.700012 14.3891 1.65763 14.3891 2.8389C14.3891 4.02018 13.4315 4.9778 12.2502 4.9778Z"
              stroke={activeFilterCount > 0 ? 'white' : 'black'}
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {activeFilterCount > 0 ? (
            <span className={styles.iconChipBadge}>{activeFilterCount}</span>
          ) : null}
        </button>
        {/* Category chip */}
        <button
          type="button"
          className={cn(
            styles.filterChip,
            activeCategoryId != null ? styles.filterChipActive : null
          )}
          onClick={() => onOpenSheet('category')}
        >
          <span>{categoryChipLabel}</span>
          {activeCategoryId != null ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('category');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : (
            <ChevDown />
          )}
        </button>
        {/* Type chip */}
        <button
          type="button"
          className={cn(styles.filterChip, typeIds?.length ? styles.filterChipActive : null)}
          onClick={() => onOpenSheet('type')}
        >
          <span>{typeChipLabel}</span>
          {typeIds?.length ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('type');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : (
            <ChevDown />
          )}
        </button>
        {/* Brand chip */}
        <button
          type="button"
          className={cn(styles.filterChip, brandIds?.length ? styles.filterChipActive : null)}
          onClick={() => onOpenSheet('brand')}
        >
          <span>{brandChipLabel}</span>
          {brandIds?.length ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('brand');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : (
            <ChevDown />
          )}
        </button>
        {/* Price chip */}
        <button
          type="button"
          className={cn(
            styles.filterChip,
            priceRange?.min != null || priceRange?.max != null ? styles.filterChipActive : null
          )}
          onClick={() => onOpenSheet('price')}
        >
          <span>{priceLabel}</span>
          {priceRange?.min != null || priceRange?.max != null ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('price');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : (
            <ChevDown />
          )}
        </button>
        {/* Original chip */}
        <button
          type="button"
          className={cn(styles.filterChip, isOriginalOnly ? styles.filterChipActive : null)}
          onClick={onToggleOriginal}
        >
          <span>Оригинал</span>
          {isOriginalOnly ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('original');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : null}
        </button>
        {/* Delivery chip */}
        <button
          type="button"
          className={cn(styles.filterChip, hasDeliveryFilter ? styles.filterChipActive : null)}
          onClick={() => onOpenSheet('delivery')}
        >
          <span>{deliveryChipLabel}</span>
          {hasDeliveryFilter ? (
            <span
              className={styles.selectedChipX}
              role="button"
              onClick={(e) => {
                e.stopPropagation();
                onClearFilter('delivery');
              }}
            >
              <img src="/icons/global/markXBlack.svg" alt="" />
            </span>
          ) : (
            <ChevDown />
          )}
        </button>
      </div>
    </div>
  );
}
