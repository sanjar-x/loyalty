"use client";
const EMPTY_SET: Set<number> = new Set();
const NOOP = (): void => {};
import React, { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import ProductImageGallery from "@/components/blocks/product/ProductImageGallery";
import ProductInfo from "@/components/blocks/product/ProductInfo";
import ProductSizes from "@/components/blocks/product/ProductSizes";
import ProductPrice from "@/components/blocks/product/ProductPrice";
import ProductAddToCart from "@/components/blocks/product/ProductAddToCart";
import ProductReviews from "@/components/blocks/product/ProductReviews";
import InfoCard from "@/components/blocks/home/InfoCard";
import ProductSection from "@/components/blocks/product/ProductSection";
import ProductShippingOptions from "@/components/blocks/product/ProductShippingOptions";
import ProductBrandsCarousel from "@/components/blocks/product/ProductBrandsCarousel";
import styles from "./page.module.css";
import cx from "clsx";
import {
  getProductPhotoCandidates,
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "@/lib/format/product-image";
import { getBrandLogoCandidates, buildBrandLogoUrl } from "@/lib/format/brand-image";
import { formatRubPrice } from "@/lib/format/price";

interface ApiProduct {
  id?: number;
  name?: string;
  price?: number | string;
  brand?: string | { id?: number | string; name?: string; title?: string; logo?: string };
  brand_name?: string;
  brand_id?: number | string;
  category_id?: number | string;
  type_id?: number | string;
  delivery?: string;
  deliveryDate?: string;
  delivery_date?: string;
  deliverySub?: string;
  delivery_sub?: string;
  image?: string;
  image_url?: string;
  photo?: string;
  photo_url?: string;
  photos?: Array<string | { filename?: string; file?: string; path?: string; url?: string }>;
  sizes?: Array<{ size?: string }>;
  is_favourite?: boolean;
  is_favorite?: boolean;
  isFavorite?: boolean;
}

interface ProductCard {
  id: number | string;
  name: string;
  price: string;
  image: string;
  imageFallbacks: string[];
  brand: string;
  deliveryDate: string;
  isFavorite: boolean;
}

interface Review {
  id: number;
  userName: string;
  avatar: string;
  date: string;
  rating: number;
  productName?: string;
  pros: string;
  cons: string;
}

interface InfoCardItem {
  title: string;
  icon: string;
}

interface BrandCarouselItem {
  id: number | string | undefined;
  name: string;
  subtitle: string;
  image: string;
  imageFallbacks: string[];
  href: string;
}

interface CategoryWithTypes {
  id?: number | string;
  name?: string;
  types?: Array<{ id?: number | string; name?: string }>;
}

interface BrandItem {
  id?: number | string;
  name?: string;
  title?: string;
  logo?: string;
}

function extractProductsList(data: unknown): ApiProduct[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if (Array.isArray((data as Record<string, unknown>).items))
      return (data as Record<string, unknown>).items as ApiProduct[];
    if (Array.isArray((data as Record<string, unknown>).results))
      return (data as Record<string, unknown>).results as ApiProduct[];
  }
  return [];
}

function mapApiProductToCard(
  product: ApiProduct | null | undefined,
  favoriteIds: Set<number>,
): ProductCard | null {
  if (!product || typeof product !== "object") return null;
  const id = product.id;
  if (id == null) return null;

  const candidates = getProductPhotoCandidates(product);
  const image = candidates[0] ?? "";
  const brandName =
    (typeof product.brand === "object" ? product.brand?.name : product.brand) ??
    product.brand_name ??
    "";

  const deliveryDate = product.delivery ? `Из ${product.delivery}` : "";

  const serverIsFavorite =
    typeof product?.is_favourite === "boolean"
      ? product.is_favourite
      : typeof product?.is_favorite === "boolean"
        ? product.is_favorite
        : typeof product?.isFavorite === "boolean"
          ? product.isFavorite
          : null;

  return {
    id,
    name: String(product.name ?? ""),
    price: formatRubPrice(product.price),
    image,
    imageFallbacks: candidates.slice(1),
    brand: String(brandName || ""),
    deliveryDate: String(deliveryDate || ""),
    isFavorite: Boolean(
      (serverIsFavorite ?? false) || (favoriteIds?.has?.(id) ?? false),
    ),
  };
}

function buildDeliveryTextFromProduct(product: ApiProduct): string {
  const deliveryRaw =
    typeof product?.delivery === "string" ? product.delivery : "";
  const delivery = deliveryRaw.trim();

  const deliveryDateRaw =
    typeof product?.deliveryDate === "string"
      ? product.deliveryDate
      : typeof product?.delivery_date === "string"
        ? product.delivery_date
        : "";
  const deliveryDate = deliveryDateRaw.trim();

  const deliverySubRaw =
    typeof product?.deliverySub === "string"
      ? product.deliverySub
      : typeof product?.delivery_sub === "string"
        ? product.delivery_sub
        : "";
  const deliverySub = deliverySubRaw.trim();

  if (deliveryDate && deliverySub) return `${deliveryDate}, ${deliverySub}`;
  if (deliveryDate && delivery) return `${deliveryDate}, из ${delivery}`;
  if (deliveryDate) return deliveryDate;
  if (delivery) return `из ${delivery}`;
  return "";
}

export default function ProductPage(): React.JSX.Element {
  const params = useParams();
  const router = useRouter();
  const productId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const productIdNum = ((): number | null => {
    const n = Number(productId);
    return Number.isFinite(n) && n > 0 ? n : null;
  })();

  // Static placeholders (API removed)
  const apiProduct: ApiProduct | null = null;
  const isProductLoading = false;
  const isProductError = false;
  const categoriesWithTypes: CategoryWithTypes[] = [];
  const brands: BrandItem[] = [];
  const addCartItem = async (): Promise<void> => {};
  const favoriteItemIds = EMPTY_SET;
  const toggleFavorite = NOOP;

  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number>(1);
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(0);
  const [isArticleCopied, setIsArticleCopied] = useState<boolean>(false);

  const isFavorite = useMemo(() => {
    if (productIdNum == null) return false;
    if (typeof apiProduct?.is_favourite === "boolean")
      return apiProduct.is_favourite;
    if (typeof apiProduct?.is_favorite === "boolean")
      return apiProduct.is_favorite;
    if (typeof apiProduct?.isFavorite === "boolean")
      return apiProduct.isFavorite;
    return favoriteItemIds.has(productIdNum);
  }, [apiProduct, favoriteItemIds, productIdNum]);

  const productImages = useMemo(() => {
    const candidates = getProductPhotoCandidates(apiProduct);
    if (candidates.length) return candidates;
    return [];
  }, [apiProduct]);

  const resolvedCategory = useMemo(() => {
    if (!apiProduct) return null;
    const list = Array.isArray(categoriesWithTypes) ? categoriesWithTypes : [];
    return (
      list.find((c) => c && String(c.id) === String(apiProduct.category_id)) ||
      null
    );
  }, [apiProduct, categoriesWithTypes]);

  const resolvedType = useMemo(() => {
    const types = Array.isArray(resolvedCategory?.types)
      ? resolvedCategory!.types!
      : [];
    return (
      types.find((t) => t && String(t.id) === String(apiProduct?.type_id)) ||
      null
    );
  }, [apiProduct, resolvedCategory]);

  const resolvedBrand = useMemo(() => {
    if (!apiProduct) return null;
    const list = Array.isArray(brands) ? brands : [];
    return (
      list.find((b) => b && String(b.id) === String(apiProduct.brand_id)) ||
      null
    );
  }, [apiProduct, brands]);

  const breadcrumb = useMemo(() => {
    const items: string[] = [];
    if (resolvedCategory?.name) items.push(resolvedCategory.name);
    if (resolvedType?.name) items.push(resolvedType.name);
    if (apiProduct?.name) items.push(apiProduct.name);
    return items.length ? items : ["Товар"];
  }, [apiProduct, resolvedCategory, resolvedType]);

  const infoCards: InfoCardItem[] = [
    { title: "Наша\n команда", icon: "/img/FriendsSection1.webp" },
    { title: "Оплата\n и сплит", icon: "/img/brokenPrice.svg" },
    { title: "Доставка \nи отслеживание", icon: "/img/FriendsSection3.webp" },
    { title: "Условия\nвозврата", icon: "/img/FriendsSection4.webp" },
    { title: "Гарантии\n и безопасность", icon: "/img/FriendsSection5.webp" },
    {
      title: "POIZON –\n только\n оригинал",
      icon: "/img/FriendsSection6.webp",
    },
    { title: "Подарочные\nкарты", icon: "/img/FriendsSection7.svg" },
    { title: "Чат\nс поддержкой", icon: "/img/FriendsSection8.webp" },
  ];

  const recommendedTabs: string[] = ["Для вас", "Похожие"];
  const [recommendedTab, setRecommendedTab] = useState<string>(recommendedTabs[0]);

  const sizes = useMemo(() => {
    const list = Array.isArray(apiProduct?.sizes) ? apiProduct!.sizes! : [];
    const mapped = list
      .map((s) => (s && typeof s === "object" ? s.size : null))
      .filter((x): x is string => typeof x === "string" && !!x.trim());
    return mapped;
  }, [apiProduct]);
  const availableSizes = sizes;

  // Static placeholders for recommended products (API removed)
  const forYouRaw: ApiProduct[] = [];
  const isForYouFetching = false;
  const isForYouLoading = false;
  const similarRaw: ApiProduct[] = [];
  const isSimilarFetching = false;
  const isSimilarLoading = false;

  const forYouProducts = useMemo(() => {
    const list = extractProductsList(forYouRaw);
    return list
      .filter((p) => String(p?.id) !== String(productIdNum))
      .map((p) => mapApiProductToCard(p, favoriteItemIds))
      .filter((p): p is ProductCard => p !== null)
      .slice(0, 12);
  }, [favoriteItemIds, forYouRaw, productIdNum]);

  const similarProducts = useMemo(() => {
    const list = extractProductsList(similarRaw);
    return list
      .filter((p) => String(p?.id) !== String(productIdNum))
      .map((p) => mapApiProductToCard(p, favoriteItemIds))
      .filter((p): p is ProductCard => p !== null)
      .slice(0, 12);
  }, [favoriteItemIds, productIdNum, similarRaw]);

  const recommendedProducts =
    recommendedTab === "Для вас" ? forYouProducts : similarProducts;
  const isRecommendedLoading =
    recommendedTab === "Для вас"
      ? Boolean(isForYouLoading || isForYouFetching)
      : Boolean(isSimilarLoading || isSimilarFetching);

  const brandsCarousel = useMemo((): BrandCarouselItem[] => {
    const b =
      resolvedBrand ??
      (apiProduct && typeof apiProduct.brand === "object"
        ? apiProduct.brand
        : null);

    if (!b) return [];

    const candidates = getBrandLogoCandidates(b);
    const image = candidates[0] || "";
    const imageFallbacks = candidates.slice(1);
    if (!image) return [];

    const name = String(
      b?.name ??
        b?.title ??
        apiProduct?.brand_name ??
        (typeof apiProduct?.brand === "string" ? apiProduct.brand : "") ??
        "",
    );
    const q = name.trim();
    const href = q ? `/search?query=${encodeURIComponent(q)}` : "#";

    return [
      {
        id: b?.id ?? apiProduct?.brand_id ?? b?.name,
        name,
        subtitle: "Бренд",
        image,
        imageFallbacks,
        href,
      },
    ];
  }, [apiProduct, resolvedBrand]);

  // Данные для отзывов
  const reviews: Review[] = [
    {
      id: 1,
      userName: "Анастасия",
      avatar: "https://i.pravatar.cc/150?img=1",
      date: "21 апреля",
      rating: 5,
      productName: "Кофта Sup...",
      pros: "стильно, классика которую можно носить под разный стиль одежды...",
      cons: "клей на подошве. ПОшив..",
    },
    {
      id: 2,
      userName: "fasffafdfa",
      avatar: "https://i.pravatar.cc/150?img=2",
      date: "21 апреля",
      rating: 4,
      pros: "стильно, классика которую можно носить под разный стиль одежды...",
      cons: "их не",
    },
  ];

  // Распределение рейтингов (для расчета среднего)
  const ratingDistribution: Record<number, number> = {
    5: 60,
    4: 20,
    3: 12,
    2: 6,
    1: 2,
  };

  const handleAddToCart = async (): Promise<void> => {
    // TODO: подключить API
  };

  const handleBuyNow = async (): Promise<void> => {
    // TODO: подключить API
  };

  const copyText = async (text: string | number): Promise<boolean> => {
    const value = String(text);

    // Modern Clipboard API (may be unavailable in some mobile/WebView contexts)
    try {
      if (
        typeof navigator !== "undefined" &&
        navigator.clipboard &&
        typeof navigator.clipboard.writeText === "function" &&
        typeof window !== "undefined" &&
        window.isSecureContext
      ) {
        await navigator.clipboard.writeText(value);
        return true;
      }
    } catch {
      // fallback below
    }

    // Fallback: hidden textarea + execCommand('copy')
    try {
      if (typeof document === "undefined") return false;
      const ta = document.createElement("textarea");
      ta.value = value;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      ta.style.top = "0";
      document.body.appendChild(ta);

      ta.focus();
      ta.select();
      try {
        ta.setSelectionRange(0, ta.value.length);
      } catch {
        // ignore
      }

      const ok = document.execCommand?.("copy") ?? false;
      document.body.removeChild(ta);
      return Boolean(ok);
    } catch {
      return false;
    }
  };

  const handleCopy = async (text: string | number): Promise<void> => {
    const ok = await copyText(text);
    if (!ok) return;
    setIsArticleCopied(true);
    window.setTimeout(() => setIsArticleCopied(false), 1200);
  };

  if (productIdNum == null) {
    return (
      <main className={cx("tg-viewport", styles.c1, styles.tw1)}>
        <Container>
          <section className={styles.hero}>
            <div className={styles.aboutTitle}>Некорректный ID товара</div>
          </section>
        </Container>
        <Footer />
      </main>
    );
  }

  if (isProductLoading && !apiProduct && !isProductError) {
    return (
      <main
        className={cx("tg-viewport", styles.c1, styles.tw1)}
        aria-busy="true"
      >
        <Container>
          <section className={styles.hero}>
            <div className={styles.skeleton}>
              <div className={cx(styles.skBlock, styles.skImage)} />
            </div>

            <div className={styles.skChips} aria-hidden="true">
              <div
                className={cx(styles.skBlock, styles.skChip, styles.skChip1)}
              />
              <div
                className={cx(styles.skBlock, styles.skChip, styles.skChip2)}
              />
              <div
                className={cx(styles.skBlock, styles.skChip, styles.skChip3)}
              />
            </div>

            <div className={styles.skInfo} aria-hidden="true">
              <div
                className={cx(styles.skBlock, styles.skLine, styles.skLine1)}
              />
              <div
                className={cx(styles.skBlock, styles.skLine, styles.skLine2)}
              />
              <div className={styles.skThumbs}>
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className={cx(styles.skBlock, styles.skThumb)} />
                ))}
              </div>
            </div>

            <div className={styles.skSizes} aria-hidden="true">
              <div
                className={cx(styles.skBlock, styles.skLine, styles.skLine1)}
              />
              <div className={styles.skSizesRow}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className={cx(styles.skBlock, styles.skSize)} />
                ))}
              </div>
            </div>
          </section>

          <section className={styles.skPrice} aria-hidden="true">
            <div className={styles.skPriceRow}>
              <div className={cx(styles.skBlock, styles.skPriceBig)} />
              <div className={cx(styles.skBlock, styles.skPriceSub)} />
            </div>
          </section>

          <section className={styles.skAbout} aria-hidden="true">
            <div className={cx(styles.skBlock, styles.skAboutTitle)} />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={styles.skAboutRow}>
                <div className={cx(styles.skBlock, styles.skAboutKey)} />
                <div className={cx(styles.skBlock, styles.skAboutVal)} />
              </div>
            ))}
          </section>

          <ProductSection
            title="Похожие"
            products={[]}
            layout="grid"
            headerVariant="tabs"
            tabs={recommendedTabs}
            activeTab={recommendedTab}
            onTabChange={setRecommendedTab}
            isLoading={true}
            onToggleFavorite={() => {}}
          />
        </Container>
        <Footer />
      </main>
    );
  }

  if (isProductError) {
    return (
      <main className={cx("tg-viewport", styles.c1, styles.tw1)}>
        <Container>
          <section className={styles.hero}>
            <div className={styles.aboutTitle}>Товар не найден</div>
            <button
              type="button"
              className={styles.supportBtn}
              onClick={() => router.back()}
            >
              Назад
            </button>
          </section>
        </Container>
        <Footer />
      </main>
    );
  }

  const productName = apiProduct?.name ?? (isProductLoading ? "Загрузка…" : "");
  const brandName =
    resolvedBrand?.name ??
    (apiProduct?.brand_name ? String(apiProduct.brand_name) : "");
  const priceText = formatRubPrice(apiProduct?.price);

  const brandQuery = String(brandName || "").trim();
  const brandSearchLink = brandQuery
    ? `/search?query=${encodeURIComponent(brandQuery)}`
    : "";

  return (
    <main className={cx("tg-viewport", styles.c1, styles.tw1)}>
      <Container>
        <section className={styles.hero}>
          {/* Галерея изображений */}
          <ProductImageGallery
            images={productImages}
            productName={productName}
            isFavorite={isFavorite}
            onToggleFavorite={() => toggleFavorite(productIdNum)}
            currentImageIndex={currentImageIndex}
            onImageChange={setCurrentImageIndex}
          />

          <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
            <div className={cx(styles.breadcrumbRow, "scrollbar-hide")}>
              {breadcrumb.map((label, idx) => {
                const isLast = idx === breadcrumb.length - 1;
                return (
                  <button
                    key={`${label}-${idx}`}
                    type="button"
                    aria-current={isLast ? "page" : undefined}
                    className={cx(
                      styles.breadcrumbChip,
                      isLast && styles.breadcrumbChipActive,
                    )}
                  >
                    <span className={styles.breadcrumbChipText}>{label}</span>
                    {!isLast ? (
                      <span
                        className={styles.breadcrumbArrow}
                        aria-hidden="true"
                      >
                        ›
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </nav>

          {/* Информация о товаре */}
          <ProductInfo
            productName={productName}
            brand={brandName}
            brandLink={brandSearchLink}
            images={productImages}
            currentImageIndex={currentImageIndex}
            onImageChange={setCurrentImageIndex}
            theme="light"
            showThumbnails={true}
          />

          {/* Выбор размера */}
          {Array.isArray(sizes) && sizes.length ? (
            <ProductSizes
              sizes={sizes}
              availableSizes={availableSizes}
              onSizeSelect={(size: string) => setSelectedSize(size)}
            />
          ) : null}
        </section>

        {/* Цена и оплата */}
        <ProductPrice
          price={priceText}
          deliveryInfo={
            apiProduct?.delivery
              ? `Доставка из ${apiProduct.delivery} до РФ 0₽`
              : ""
          }
          splitPayment={{
            count: 4,
            amount: (() => {
              const n = Number(apiProduct?.price);
              if (!Number.isFinite(n) || n <= 0) return "0";
              return String(Math.ceil(n / 4));
            })(),
            text: "без переплаты",
          }}
        />

        <ProductShippingOptions
          pickupDate="Сегодня"
          pickupSub="из наличия"
          pickupAddress="Оренбург, улица Пролетарская, 23, 2 этаж"
          deliveryDate="Послезавтра"
          deliverySub="из наличия"
          deliveryHint="В пункт выдачи от 99₽"
        />

        <ProductBrandsCarousel brands={brandsCarousel} />

        <section className={styles.cardsOuter}>
          <div className={cx(styles.cardsRow, "scrollbar-hide")}>
            {infoCards.map((c, index) => (
              <div key={c.title} className={styles.cardItem}>
                <InfoCard title={c.title} iconSrc={c.icon} index={index} />
              </div>
            ))}
          </div>
        </section>

        {/* Отзывы */}
        <ProductReviews
          brandName="Supreme"
          reviews={reviews}
          ratingDistribution={ratingDistribution}
          productImages={productImages.slice(0, 2)}
        />

        <section className={styles.about}>
          <h2 className={styles.aboutTitle}>О товаре</h2>

          <div className={styles.aboutGrid}>
            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Артикул
                <p></p>
              </span>
              <span className={styles.aboutVal}>
                <span className={styles.aboutValRow}>
                  <span>
                    {apiProduct?.id != null ? String(apiProduct.id) : "—"}
                  </span>
                  <button
                    type="button"
                    className={styles.copyBtn}
                    aria-label="Скопировать артикул"
                    onClick={() => handleCopy(apiProduct?.id ?? "")}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="18"
                      height="18"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <rect x="9" y="9" width="13" height="13" rx="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                  </button>
                  <span
                    className={styles.copiedHint}
                    aria-live="polite"
                    role="status"
                  >
                    {isArticleCopied ? "Скопировано" : ""}
                  </span>
                </span>
              </span>
            </div>

            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Категория
                <p></p>
              </span>
              <span className={styles.aboutVal}>
                {resolvedCategory?.name ?? "—"}
              </span>
            </div>

            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Тип
                <p></p>
              </span>
              <span className={styles.aboutVal}>
                {resolvedType?.name ?? "—"}
              </span>
            </div>

            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Бренд
                <p></p>
              </span>
              <span className={styles.aboutVal}>{brandName || "—"}</span>
            </div>
          </div>

          <button type="button" className={styles.supportBtn}>
            Чат с поддержкой
          </button>
        </section>

        <ProductSection
          title="Похожие"
          products={recommendedProducts}
          layout="grid"
          headerVariant="tabs"
          tabs={recommendedTabs}
          activeTab={recommendedTab}
          onTabChange={setRecommendedTab}
          isLoading={isRecommendedLoading}
          onToggleFavorite={toggleFavorite}
        />

        {/* Кнопка добавления в корзину (фиксированная внизу на mobile) */}
        <ProductAddToCart
          quantity={quantity}
          onQuantityChange={setQuantity}
          onAddToCart={handleAddToCart}
          onBuyNow={handleBuyNow}
        />
      </Container>
      <Footer />
    </main>
  );
}
