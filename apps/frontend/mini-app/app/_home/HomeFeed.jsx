import FriendsSection from '@/components/blocks/home/FriendsSection';
import HomeDeliveryStatusCard from '@/components/blocks/home/HomeDeliveryStatusCard';
import ProductSection from '@/components/blocks/product/ProductSection';
import { useDragToScroll } from '@/lib/hooks/useDragToScroll';
import { MAX_AUTO_RETRIES } from '@/lib/home/useForYouFeed';

import styles from '../page.module.css';

/**
 * Bosh sahifa "home mode" kontenti — друзья, доставка, "Только что купили"
 * (trending), "Для вас" (recommended feed) + load-more / retry holati +
 * IntersectionObserver sentinel. Audit #1: `app/page.jsx`'dan ajratildi.
 *
 * Sahifa uni faqat `isHomeMode` da render qiladi. `useForYouFeed` sahifada
 * chaqiriladi (results mode'da ham fetch bo'lishi uchun) — bu komponent uning
 * natijasini prop sifatida oladi; `sentinelRef` o'sha hook'niki.
 *
 * `deliveryStatusScrollRef` (desktop drag-to-scroll) shu yerda lokal.
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
  // sectionSpacing — HomeDeliveryStatusCard'lar gorizontal ro'yxati uchun
  // desktop drag-to-scroll. Mobile'da hook native swipe'ga aralashmaydi.
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
