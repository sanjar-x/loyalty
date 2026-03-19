"use client";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import ProductSection from "@/components/blocks/product/ProductSection";
import { useMemo, useState } from "react";
import styles from "./page.module.css";

export default function ViewedPage() {
  const [viewedProducts, setViewedProducts] = useState([
    {
      id: 1,
      name: "Туфли Prada Monolith Brushed Original Bla...",
      brand: "Prada",
      price: "112 490 ₽",
      image: "/products/shoes-1.png",
      isFavorite: false,
      deliveryDate: "30 марта",
    },
    {
      id: 2,
      name: "Лонгслив Comme Des Garcons Play",
      brand: "Comme Des Garcons",
      price: "12 990 ₽",
      image: "/products/t-shirt-1.png",
      isFavorite: false,
      deliveryDate: "Послезавтра",
    },
    {
      id: 3,
      name: "Футболка Daze",
      brand: "Daze",
      price: "2 890 ₽",
      image: "/products/t-shirt-2.png",
      isFavorite: false,
      deliveryDate: "30 марта",
    },
    {
      id: 4,
      name: "Футболка Daze",
      brand: "Daze",
      price: "8 990 ₽",
      image: "/products/t-shirt-2.png",
      isFavorite: false,
      deliveryDate: "30 марта",
    },
    {
      id: 5,
      name: "Куртка зимняя",
      brand: "NoName",
      price: "15 990 ₽",
      image: "/products/t-shirt-2.png",
      isFavorite: false,
      deliveryDate: "30 марта",
    },
    {
      id: 6,
      name: "Куртка зимняя",
      brand: "NoName",
      price: "15 990 ₽",
      image: "/products/t-shirt-2.png",
      isFavorite: false,
      deliveryDate: "Послезавтра",
    },
  ]);

  const toggleViewedProduct = (id) => {
    setViewedProducts((prev) =>
      prev.map((product) =>
        product.id === id
          ? { ...product, isFavorite: !product.isFavorite }
          : product,
      ),
    );
  };

  const date = useMemo(() => {
    try {
      return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "long",
      }).format(new Date());
    } catch {
      return "";
    }
  }, []);

  return (
    <div className={styles.pageViewed}>
      <Header title="Просмотренное"></Header>
      <main className={styles.c1}>
        <div className={styles.c2}>
          <div className={styles.c3}>
            <span suppressHydrationWarning className={styles.c4}>
              {date}
            </span>
          </div>
          <ProductSection
            isViewed={true}
            onToggleFavorite={toggleViewedProduct}
            products={viewedProducts}
          />
        </div>
      </main>

      <Footer />
    </div>
  );
}
