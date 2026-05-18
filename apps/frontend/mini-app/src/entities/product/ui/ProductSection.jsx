'use client';
import ProductCard from './ProductCard';

import { useState } from 'react';

import { useDragToScroll } from '@/shared/lib/hooks';
import { cn } from '@/shared/lib/ui-utils';
import styles from './ProductSection.module.css';

export default function ProductSection({
  isPurchased,
  isViewed,
  title = '',
  products = [],
  onToggleFavorite = (_id) => {},
  favoriteItemIds,
  layout = 'grid',
  isLoading = false,
  skeletonCount,
  hideFavoriteButton = false,
  viewAllHref,
  cardProps = {},
  headerVariant = 'title',
  tabs = ['Для вас', 'Похожие'],
  activeTab,
  onTabChange,
}) {
  const effectiveSkeletonCount =
    typeof skeletonCount === 'number' && Number.isFinite(skeletonCount)
      ? Math.max(0, Math.trunc(skeletonCount))
      : layout === 'horizontal'
        ? 5
        : 6;

  const isControlled = activeTab !== undefined;
  const defaultTab = (() => {
    if (activeTab !== undefined) return activeTab;
    if (Array.isArray(tabs) && tabs.length > 0) {
      if (typeof title === 'string' && tabs.includes(title)) return title;
      return tabs[0];
    }
    return typeof title === 'string' ? title : '';
  })();
  const [internalTab, setInternalTab] = useState(defaultTab);
  const currentTab = isControlled ? activeTab : internalTab;

  // Desktop drag-to-scroll + wheel proxy only for horizontal layout.
  // On mobile/touch the hook itself early-returns on `pointerType === "touch"`,
  // so native swipe is fully preserved.
  const horizontalRowRef = useDragToScroll();

  if (isLoading) {
    if (layout === 'horizontal') {
      return (
        <section className={styles.sectionHorizontal} aria-busy="true">
          {title ? (
            <div className={styles.header}>
              <h2 className={styles.titleHorizontal}>{title}</h2>
              {viewAllHref ? (
                <button
                  type="button"
                  className={styles.allBtn}
                  onClick={() => {
                    const tg = typeof window !== 'undefined' && window.Telegram?.WebApp;
                    if (tg?.openLink) tg.openLink(viewAllHref);
                    else window.open(viewAllHref, '_blank', 'noopener');
                  }}
                >
                  <span className={styles.allText}>все</span>
                  <img className={styles.arrow} src="/icons/global/arrowGrey.svg" alt="arrow" />
                </button>
              ) : (
                <button type="button" className={styles.allBtn} disabled>
                  <span className={styles.allText}>все</span>
                  <img className={styles.arrow} src="/icons/global/arrowGrey.svg" alt="arrow" />
                </button>
              )}
            </div>
          ) : null}

          <div className={cn(styles.row, 'scrollbar-hide')} aria-hidden="true">
            {Array.from({ length: effectiveSkeletonCount }).map((_, idx) => (
              <div key={idx} className={styles.skeletonCardCompact}>
                <div className={styles.skeletonImage} />
                <div className={styles.skeletonPrice} />
                <div className={styles.skeletonName} />
                <div className={styles.skeletonDelivery} />
              </div>
            ))}
          </div>
        </section>
      );
    }

    return (
      <section className={styles.sectionGrid} aria-busy="true">
        {title ? (
          <div className={styles.header}>
            <h2 className={styles.titleGrid}>{title}</h2>
          </div>
        ) : null}

        <div className={styles.grid} aria-hidden="true">
          {Array.from({ length: effectiveSkeletonCount }).map((_, idx) => (
            <div key={idx} className={styles.skeletonCardNormal}>
              <div className={styles.skeletonImage} />
              <div className={styles.skeletonDots} />
              <div className={styles.skeletonPrice} />
              <div className={styles.skeletonName} />
              <div className={styles.skeletonDelivery} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (layout === 'horizontal') {
    return (
      <section className={styles.sectionHorizontal}>
        {title ? (
          <div className={styles.header}>
            <h2 className={styles.titleHorizontal}>{title}</h2>
            {viewAllHref ? (
              <a
                href={viewAllHref}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.allBtn}
              >
                <span className={styles.allText}>все</span>
                <img className={styles.arrow} src="/icons/global/arrowGrey.svg" alt="arrow" />
              </a>
            ) : (
              <button type="button" className={styles.allBtn}>
                <span className={styles.allText}>все</span>
                <img className={styles.arrow} src="/icons/global/arrowGrey.svg" alt="arrow" />
              </button>
            )}
          </div>
        ) : null}
        <div ref={horizontalRowRef} className={cn(styles.row, 'scrollbar-hide')}>
          {products?.map((product) => (
            <ProductCard
              isPurchased={isPurchased}
              isViewed={isViewed}
              key={product.id}
              product={product}
              onToggleFavorite={onToggleFavorite}
              favoriteItemIds={favoriteItemIds}
              variant="compact"
              hideFavoriteButton={hideFavoriteButton}
              {...cardProps}
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className={`${styles.sectionGrid} ${isViewed ? `${styles.sectionGridViewed}` : ''}`}>
      {headerVariant === 'tabs' && Array.isArray(tabs) && tabs.length ? (
        <div className={styles.tabsHeader} role="tablist" aria-label="Раздел">
          {tabs.map((tab) => {
            const isActive = tab === currentTab;
            return (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={cn(styles.chip, isActive && styles.chipActive)}
                onClick={() => {
                  if (!isControlled) setInternalTab(tab);
                  onTabChange?.(tab);
                }}
              >
                {tab}
              </button>
            );
          })}
        </div>
      ) : title ? (
        <div className={styles.header}>
          <h2 className={styles.titleGrid}>{title}</h2>
        </div>
      ) : null}
      <div className={styles.grid}>
        {products?.map((product) => (
          <ProductCard
            isViewed={isViewed}
            isPurchased={isPurchased}
            key={product.id}
            product={product}
            onToggleFavorite={onToggleFavorite}
            favoriteItemIds={favoriteItemIds}
            variant="normal"
            hideFavoriteButton={hideFavoriteButton}
            {...cardProps}
          />
        ))}
      </div>
    </section>
  );
}
