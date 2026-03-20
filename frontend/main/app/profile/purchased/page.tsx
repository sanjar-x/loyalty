"use client";
import Footer from "@/components/layout/Footer";
import ProductSection from "@/components/blocks/product/ProductSection";
import BottomSheet from "@/components/ui/BottomSheet";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

interface PurchasedProduct {
  id: number;
  name: string;
  brand: string;
  price: string;
  image: string;
  isFavorite: boolean;
  deliveryDate: string;
  rating?: number;
}

function parsePriceRub(value: string | undefined): number {
  const raw = String(value ?? "");
  const digits = raw.replace(/[^0-9]/g, "");
  const n = Number(digits);
  return Number.isFinite(n) ? n : 0;
}

const SORT_OPTIONS = [
  { key: "new", label: "Новые" },
  { key: "old", label: "Старые" },
  { key: "cheap", label: "Подешевле" },
  { key: "expensive", label: "Подороже" },
] as const;

type SortKey = (typeof SORT_OPTIONS)[number]["key"];

const RATINGS_KEY = "lm:purchasedRatings";
const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

const EMPTY_OBJECT: Record<string, unknown> = Object.freeze({});

function useLocalStorageObject(key: string, changeEventName: string): Record<string, unknown> {
  const cacheRef = useRef({
    lastRaw: null as string | null,
    lastValue: EMPTY_OBJECT as Record<string, unknown>,
  });

  const getSnapshot = (): Record<string, unknown> => {
    let raw: string | null = null;
    try {
      raw = localStorage.getItem(key);
    } catch {
      raw = null;
    }

    if (raw === cacheRef.current.lastRaw) return cacheRef.current.lastValue;

    let nextValue: Record<string, unknown> = EMPTY_OBJECT;
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          nextValue = parsed as Record<string, unknown>;
        }
      } catch {
        nextValue = EMPTY_OBJECT;
      }
    }

    cacheRef.current.lastRaw = raw;
    cacheRef.current.lastValue = nextValue;
    return nextValue;
  };

  return useSyncExternalStore(
    (onStoreChange) => {
      const handler = () => onStoreChange();
      window.addEventListener("storage", handler);
      window.addEventListener(changeEventName, handler);
      return () => {
        window.removeEventListener("storage", handler);
        window.removeEventListener(changeEventName, handler);
      };
    },
    getSnapshot,
    () => EMPTY_OBJECT,
  );
}

export default function PurchasedPage() {
  const router = useRouter();

  useEffect(() => {
    document.title = "Купленные товары";
  }, []);

  const ratingsFromStorage = useLocalStorageObject(RATINGS_KEY, "lm:ratings");

  const [purchasedProducts, setPurchasedProducts] = useState<PurchasedProduct[]>(() => []);

  const toggleFavorite = (id: string | number) => {
    setPurchasedProducts((prev) =>
      prev.map((product) =>
        product.id === id
          ? { ...product, isFavorite: !product.isFavorite }
          : product,
      ),
    );
  };

  const setRating = (id: string | number | undefined, rating: number) => {
    if (!id) return;

    try {
      const saved =
        ratingsFromStorage && typeof ratingsFromStorage === "object"
          ? ratingsFromStorage
          : EMPTY_OBJECT;
      const next = { ...saved };
      next[id] = rating;
      localStorage.setItem(RATINGS_KEY, JSON.stringify(next));
    } catch {
      // ignore
    } finally {
      try {
        window.dispatchEvent(new Event("lm:ratings"));
      } catch {
        // ignore
      }
    }
  };

  const handleStarSelect = (id: string | number | undefined, rating: number) => {
    setRating(id, rating);
    if (!id) return;

    try {
      const product = purchasedProducts.find((p) => p.id === id);
      if (product) {
        const raw = localStorage.getItem(REVIEW_PRODUCTS_KEY);
        const saved = raw ? JSON.parse(raw) : {};
        const next: Record<string, unknown> =
          saved && typeof saved === "object" && !Array.isArray(saved)
            ? { ...saved }
            : {};

        next[id] = {
          ...product,
          rating,
          image: product.image,
        };
        localStorage.setItem(REVIEW_PRODUCTS_KEY, JSON.stringify(next));
      }
    } catch {
      // ignore
    }

    router.push(`/profile/purchased/review/${id}?rating=${rating}`);
  };

  const [isSortOpen, setIsSortOpen] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("new");
  const [pendingSortKey, setPendingSortKey] = useState<SortKey>(sortKey);

  const sortLabel =
    SORT_OPTIONS.find((x) => x.key === sortKey)?.label ?? "Новые";

  const displayedProducts = useMemo(() => {
    const list = Array.isArray(purchasedProducts) ? [...purchasedProducts] : [];

    switch (sortKey) {
      case "old":
        list.sort((a, b) => (a?.id ?? 0) - (b?.id ?? 0));
        break;
      case "cheap":
        list.sort((a, b) => parsePriceRub(a?.price) - parsePriceRub(b?.price));
        break;
      case "expensive":
        list.sort((a, b) => parsePriceRub(b?.price) - parsePriceRub(a?.price));
        break;
      case "new":
      default:
        list.sort((a, b) => (b?.id ?? 0) - (a?.id ?? 0));
        break;
    }

    return list.map((p) => ({
      ...p,
      rating:
        typeof ratingsFromStorage?.[p.id] === "number"
          ? (ratingsFromStorage[p.id] as number)
          : (p.rating ?? 0),
    }));
  }, [purchasedProducts, ratingsFromStorage, sortKey]);

  return (
    <div className="tg-viewport">
      <main className={styles.c1}>
        <h3 className={styles.title}>Купленные товары</h3>
        <div className={styles.c2}>
          <button
            className={styles.filterBtn}
            type="button"
            onClick={() => {
              setPendingSortKey(sortKey);
              setIsSortOpen(true);
            }}
          >
            <img src="/icons/global/filterIcon.svg" alt="icon" />
            <span>{sortLabel}</span>
          </button>

          <BottomSheet
            open={isSortOpen}
            title="Показывать сначала"
            onClose={() => setIsSortOpen(false)}
            footer={
              <div className={styles.sheetFooter}>
                <button
                  type="button"
                  className={styles.sheetBtnSecondary}
                  onClick={() => {
                    setPendingSortKey(sortKey);
                    setIsSortOpen(false);
                  }}
                >
                  Отменить
                </button>
                <button
                  type="button"
                  className={styles.sheetBtnPrimary}
                  onClick={() => {
                    setSortKey(pendingSortKey);
                    setIsSortOpen(false);
                  }}
                >
                  Применить
                </button>
              </div>
            }
          >
            <div className={styles.sheetList}>
              {SORT_OPTIONS.map((opt) => {
                const checked = opt.key === pendingSortKey;
                return (
                  <button
                    key={opt.key}
                    type="button"
                    className={styles.sheetRow}
                    onClick={() => setPendingSortKey(opt.key)}
                  >
                    <span className={styles.sheetLabel}>{opt.label}</span>
                    <span
                      className={
                        checked
                          ? `${styles.radio} ${styles.radioChecked}`
                          : styles.radio
                      }
                      aria-hidden="true"
                    />
                  </button>
                );
              })}
            </div>
          </BottomSheet>

          {displayedProducts.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#999" }}>
              Нет данных
            </div>
          ) : (
            <>
              <ProductSection
                isPurchased={true}
                products={displayedProducts}
                onToggleFavorite={toggleFavorite}
                layout="grid"
                cardProps={{
                  showStars: true,
                  starsInteractive: true,
                  onStarSelect: handleStarSelect,
                }}
              />

              <ProductSection
                title="Для вас"
                products={displayedProducts}
                onToggleFavorite={toggleFavorite}
                layout="grid"
                cardProps={{
                  showStars: true,
                  starsInteractive: true,
                  onStarSelect: handleStarSelect,
                }}
              />
            </>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
