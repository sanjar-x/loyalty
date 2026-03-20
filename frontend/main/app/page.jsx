"use client";

import SearchBar from "@/components/blocks/search/SearchBar";
import Footer from "@/components/layout/Footer";
import CategoryTabs from "@/components/blocks/home/CategoryTabs";
import FriendsSection from "@/components/blocks/home/FriendsSection";
import HomeDeliveryStatusCard from "@/components/blocks/home/HomeDeliveryStatusCard";
import ProductSection from "@/components/blocks/product/ProductSection";

import styles from "./page.module.css";

export default function Home() {
  const recentProducts = [];
  const recommendedProducts = [];
  const toggleFavorite = () => {};
  const isLatestInitialLoading = false;
  const isRecommendedInitialLoading = false;

  return (
    <div
      className="lm-app-bg"
      style={{ minHeight: "var(--tg-viewport-height)" }}
    >
      <div className={styles.container}>
        <SearchBar navigateOnFocusTo="/search" readOnly />
        <CategoryTabs />
        <FriendsSection />

        <div className={styles.sectionSpacing}>
          <HomeDeliveryStatusCard />
          <HomeDeliveryStatusCard />
        </div>

        <ProductSection
          title="Только что купили"
          products={recentProducts}
          onToggleFavorite={toggleFavorite}
          layout="horizontal"
          isLoading={isLatestInitialLoading}
          skeletonCount={5}
        />

        <ProductSection
          title="Для вас"
          products={recommendedProducts}
          onToggleFavorite={toggleFavorite}
          layout="grid"
          isLoading={isRecommendedInitialLoading}
          skeletonCount={6}
        />

        <Footer />
      </div>
    </div>
  );
}
