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
import { mockPurchasedProducts } from "./mockPurchasedProducts";

function parsePriceRub(value) {
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
];

const RATINGS_KEY = "lm:purchasedRatings";
const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

const EMPTY_OBJECT = Object.freeze({});

function useLocalStorageObject(key, changeEventName) {
  // `getSnapshot` must return the same reference when the underlying data
  // hasn't changed, otherwise React can enter an update loop.
  const cacheRef = useRef({
    lastRaw: null,
    lastValue: EMPTY_OBJECT,
  });

  const getSnapshot = () => {
    let raw = null;
    try {
      raw = localStorage.getItem(key);
    } catch {
      raw = null;
    }

    if (raw === cacheRef.current.lastRaw) return cacheRef.current.lastValue;

    let nextValue = EMPTY_OBJECT;
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          nextValue = parsed;
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
      // 'storage' fires for other tabs; we also dispatch a custom event for same-tab updates.
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
    // Telegram WebApp topbar title odatda document.title dan olinadi.
    document.title = "Купленные товары";
  }, []);

  const ratingsFromStorage = useLocalStorageObject(RATINGS_KEY, "lm:ratings");

  // IMPORTANT: Don't read `localStorage` in the initial state initializer.
  // Client Components still render on the server, and differing initial state
  // causes hydration mismatches (e.g. stars active vs inactive).
  const [purchasedProducts, setPurchasedProducts] = useState(() =>
    mockPurchasedProducts.map((p) => ({ ...p, rating: p.rating ?? 0 })),
  );

  const toggleFavorite = (id) => {
    setPurchasedProducts((prev) =>
      prev.map((product) =>
        product.id === id
          ? { ...product, isFavorite: !product.isFavorite }
          : product,
      ),
    );
  };

  const setRating = (id, rating) => {
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
      // Ensure same-tab subscribers update.
      try {
        window.dispatchEvent(new Event("lm:ratings"));
      } catch {
        // ignore
      }
    }
  };

  const handleStarSelect = (id, rating) => {
    setRating(id, rating);
    if (!id) return;

    try {
      const product = purchasedProducts.find((p) => p.id === id);
      if (product) {
        const imageFromMock = mockPurchasedProducts.find(
          (p) => p.id === id,
        )?.image;
        const raw = localStorage.getItem(REVIEW_PRODUCTS_KEY);
        const saved = raw ? JSON.parse(raw) : {};
        const next =
          saved && typeof saved === "object" && !Array.isArray(saved)
            ? { ...saved }
            : {};

        next[id] = {
          ...product,
          rating,
          image: product.image || imageFromMock,
        };
        localStorage.setItem(REVIEW_PRODUCTS_KEY, JSON.stringify(next));
      }
    } catch {
      // ignore
    }

    router.push(`/profile/purchased/review/${id}?rating=${rating}`);
  };

  const [isSortOpen, setIsSortOpen] = useState(false);
  const [sortKey, setSortKey] = useState("new");
  const [pendingSortKey, setPendingSortKey] = useState(sortKey);

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
          ? ratingsFromStorage[p.id]
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
        </div>
      </main>
      <Footer />
    </div>
  );
}
