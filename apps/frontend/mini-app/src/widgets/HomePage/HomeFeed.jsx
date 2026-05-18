import FriendsSection from '@/features/home-feed/ui/FriendsSection';
import HomeDeliveryStatusCard from '@/features/home-feed/ui/HomeDeliveryStatusCard';
import ProductSection from '@/entities/product';
import { useDragToScroll } from '@/shared/lib/hooks';
import { MAX_AUTO_RETRIES } from '@/features/home-feed';

import styles from './page.module.css';

/**
 * Home page "home mode" content — friends, delivery, "Только что купили"
 * (trending), "Для вас" (recommended feed) + load-more / retry state +
 * IntersectionObserver sentinel. Audit #1: split out of `app/page.jsx`.
 *
 * The page renders it only in `isHomeMode`. `useForYouFeed` is called on
 * the page (so it also fetches in results mode) — this component takes
 * its result as a prop; `sentinelRef` comes from that hook.
 *
 * `deliveryStatusScrollRef` (desktop drag-to-scroll) is local here.
 */
export default function HomeFeed({
  recentProducts,
  isLatestInitialLoading,
  recommendedProducts,
  isRecommendedInitialLoading,
  isRecommendedLoadingMore,
  isRecommendedRetryPending,
  loadMoreError,
  retryLoadMore,
  sentinelRef,
  favoriteItemIds,
  toggleFavorite,
}) {
  // sectionSpacing — desktop drag-to-scroll for the horizontal list of
  // HomeDeliveryStatusCards. On mobile the hook doesn't interfere with
  // the native swipe.
  const deliveryStatusScrollRef = useDragToScroll();

  return (
    <>
      <FriendsSection />

      <div ref={deliveryStatusScrollRef} className={styles.sectionSpacing}>
        <HomeDeliveryStatusCard />
        <HomeDeliveryStatusCard />
      </div>

      {recentProducts.length > 0 || isLatestInitialLoading ? (
        <ProductSection
          title="Только что купили"
          products={recentProducts}
          onToggleFavorite={toggleFavorite}
          favoriteItemIds={favoriteItemIds}
          layout="horizontal"
          isLoading={isLatestInitialLoading}
          skeletonCount={5}
          viewAllHref="https://t.me/loyaltystream"
        />
      ) : null}

      {recommendedProducts.length > 0 || isRecommendedInitialLoading ? (
        <ProductSection
          title="Для вас"
          products={recommendedProducts}
          onToggleFavorite={toggleFavorite}
          favoriteItemIds={favoriteItemIds}
          layout="grid"
          isLoading={isRecommendedInitialLoading}
          skeletonCount={6}
        />
      ) : null}

      {isRecommendedLoadingMore || isRecommendedRetryPending ? (
        <div className={styles.loadMore} aria-live="polite" aria-busy="true">
          <div className={styles.spinner} aria-hidden="true" />
          <div className={styles.loadMoreText}>
            {loadMoreError?.transient && !loadMoreError?.exhausted
              ? `Повторная попытка (${loadMoreError.attempt}/${MAX_AUTO_RETRIES})…`
              : 'Загрузка…'}
          </div>
        </div>
      ) : loadMoreError?.exhausted ? (
        <div className={styles.loadMore} role="alert" aria-live="polite">
          <div className={styles.loadMoreText}>Не удалось загрузить больше товаров.</div>
          <button type="button" className={styles.retryBtn} onClick={retryLoadMore}>
            Повторить
          </button>
        </div>
      ) : null}

      <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />
    </>
  );
}
