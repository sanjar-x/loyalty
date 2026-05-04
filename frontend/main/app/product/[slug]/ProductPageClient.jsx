"use client";
import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import ProductImageGallery from "@/components/blocks/product/ProductImageGallery";
import ProductInfo from "@/components/blocks/product/ProductInfo";
import ProductSkuSelector from "@/components/blocks/product/ProductSkuSelector";
import ProductPrice from "@/components/blocks/product/ProductPrice";
import ProductAddToCart from "@/components/blocks/product/ProductAddToCart";
import InfoCard from "@/components/blocks/home/InfoCard";
import ProductSection from "@/components/blocks/product/ProductSection";
import ProductShippingOptions from "@/components/blocks/product/ProductShippingOptions";
import ProductBrandsCarousel from "@/components/blocks/product/ProductBrandsCarousel";
import {
  useAddCartItemMutation,
  useGetProductByIdQuery,
  useGetSimilarProductsQuery,
  useGetForYouFeedQuery,
  useGetProductMediaQuery,
} from "@/lib/store/api";
import { useItemFavorites } from "@/lib/hooks/useItemFavorites";
import { mapProductCard } from "@/lib/format/mapProductCard";
import ProductSizes from "@/components/blocks/product/ProductSizes";
import styles from "./page.module.css";
import cx from "clsx";
import {
  buildBackendAssetUrl,
  buildBrandLogoUrl,
  buildProductPhotoUrl,
} from "@/lib/format/backendAssets";
import {
  getGalleryImages,
  getSizeGuideUrl,
  deriveSizesFromSkus,
} from "@/lib/product/attributes";

function uniqStrings(arr) {
  const out = [];
  const seen = new Set();
  for (const v of arr) {
    const s = typeof v === "string" ? v : "";
    if (!s) continue;
    if (seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

function getBrandLogoCandidates(brand) {
  const id = brand?.id;
  const logo =
    brand?.logo ??
    brand?.logo_path ??
    brand?.logoUrl ??
    brand?.image ??
    brand?.image_url;

  const byPath = buildBrandLogoUrl(logo);

  const byId =
    id != null
      ? `/api/backend/api/v1/brands/${encodeURIComponent(String(id))}/logo`
      : "";

  return uniqStrings([
    byPath,
    byId,
    buildBackendAssetUrl(logo),
    buildBackendAssetUrl(logo, ["media"]),
    buildBackendAssetUrl(logo, ["static"]),
    buildBackendAssetUrl(logo, ["uploads"]),
  ]);
}

function formatRub(amount) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return "—";
  const formatted = Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

function extractProductsList(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.results)) return data.results;
  }
  return [];
}

function extractPhotoFilename(entry) {
  if (typeof entry === "string") return entry.trim();
  if (entry && typeof entry === "object") {
    const v = entry.filename ?? entry.file ?? entry.path ?? entry.url;
    return typeof v === "string" ? v.trim() : "";
  }
  return "";
}

function getProductPhotoCandidates(product) {
  const seen = new Set();
  const result = [];

  const addUrl = (url) => {
    if (!url || seen.has(url)) return;
    seen.add(url);
    result.push(url);
  };

  // Primary: mapped product.images[] (from media[]/image)
  if (Array.isArray(product?.images)) {
    for (const u of product.images) {
      if (typeof u === "string" && u.trim()) addUrl(u.trim());
    }
  }

  // Primary single
  const rawDirect =
    (typeof product?.image === "string" ? product.image : "") ||
    (typeof product?.image_url === "string" ? product.image_url : "") ||
    (typeof product?.photo === "string" ? product.photo : "") ||
    (typeof product?.photo_url === "string" ? product.photo_url : "");
  if (rawDirect && rawDirect.trim()) {
    addUrl(buildProductPhotoUrl(rawDirect.trim()));
  }

  // Legacy `photos` array fallback
  const photos = Array.isArray(product?.photos) ? product.photos : [];
  for (const entry of photos) {
    const raw = extractPhotoFilename(entry);
    if (raw) {
      addUrl(buildProductPhotoUrl(raw));
    }
  }

  return result;
}

function buildDeliveryTextFromProduct(product) {
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

// `mapProductCard` olib tashlandi — `lib/format/mapProductCard.js`
// orqali umumiy `mapProductCard()` ishlatiladi. Quyidagi `recommended`
// (Для вас/Похожие) sectionlari uchun shu mapper ishlatiladi.

function buildSkuOptions(product) {
  const skus = Array.isArray(product?.skus) ? product.skus : [];
  if (!skus.length) return [];

  // Try to label SKU by common suffix in skuCode (e.g., -001, -002 → 1, 2).
  return skus.map((s, idx) => {
    const code = String(s.skuCode || "");
    const suffix = code.match(/-(\d+)$/)?.[1] ?? String(idx + 1);
    const label = String(Number(suffix));
    return {
      id: s.id,
      label,
      sublabel: code || `Вариант ${idx + 1}`,
      isAvailable: s.isActive !== false,
      price: s.resolvedPrice,
    };
  });
}

function extractCategoryInfoFromBreadcrumbs(product) {
  const crumbs = Array.isArray(product?.breadcrumbs) ? product.breadcrumbs : [];
  // breadcrumbs ordered root → leaf. Typically: [category, type].
  const category = crumbs[0] ?? null;
  const type = crumbs.length > 1 ? crumbs[crumbs.length - 1] : null;
  return { category, type };
}

export default function ProductPageClient({ slug }) {
  const router = useRouter();

  const {
    data: fetched,
    isLoading: isProductLoading,
    isError: isProductError,
  } = useGetProductByIdQuery(slug, { skip: !slug });

  const apiProduct = fetched ?? null;

  const productIdNum = useMemo(() => {
    const rawId = apiProduct?.id;
    if (rawId == null) return null;
    const asNum = Number(rawId);
    if (Number.isFinite(asNum) && asNum > 0) return asNum;
    return rawId; // string id/slug — still valid for favorites/cart meta keys
  }, [apiProduct?.id]);

  const [addCartItem] = useAddCartItemMutation();
  const { favoriteItemIds, toggleFavorite } = useItemFavorites("product");

  const [selectedVariantId, setSelectedVariantId] = useState(null);
  const [selectedSkuId, setSelectedSkuId] = useState(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [isArticleCopied, setIsArticleCopied] = useState(false);

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

  // Fetch gallery media via /products/{id}/media for variant-aware image display.
  const inlineCandidates = useMemo(
    () => getProductPhotoCandidates(apiProduct),
    [apiProduct],
  );

  const mediaProductId =
    apiProduct && typeof apiProduct === "object" ? apiProduct.id : null;

  const { data: allMediaAssets = [] } = useGetProductMediaQuery(
    { productId: mediaProductId, limit: 50 },
    { skip: !mediaProductId },
  );

  // Resolve selectedVariantId: default to first variant when product loads
  const variants = Array.isArray(apiProduct?.variants) ? apiProduct.variants : [];
  const resolvedVariantId = useMemo(() => {
    if (selectedVariantId && variants.some((v) => v.id === selectedVariantId)) {
      return selectedVariantId;
    }
    return variants[0]?.id ?? null;
  }, [selectedVariantId, variants]);

  // Gallery images for the active variant (or product-level if no variant match)
  const productImages = useMemo(() => {
    if (allMediaAssets.length) {
      const variantImages = getGalleryImages(allMediaAssets, resolvedVariantId);
      if (variantImages.length) return variantImages;
      // Fallback to any product-level gallery images
      const productLevel = getGalleryImages(allMediaAssets, null);
      if (productLevel.length) return productLevel;
    }
    // Final fallback to inline images from storefront response
    return inlineCandidates;
  }, [allMediaAssets, resolvedVariantId, inlineCandidates]);

  // Size guide image URL (from role=size_guide asset)
  const sizeGuideUrl = useMemo(
    () => getSizeGuideUrl(allMediaAssets),
    [allMediaAssets],
  );

  // Size options from active variant's SKUs
  const selectedVariant = useMemo(
    () => variants.find((v) => v.id === resolvedVariantId) ?? null,
    [variants, resolvedVariantId],
  );

  const sizeOptions = useMemo(
    () => deriveSizesFromSkus(selectedVariant?.skus),
    [selectedVariant],
  );

  // Category/type resolved from embedded breadcrumbs (no extra eager fetch).
  const { category: resolvedCategory, type: resolvedType } = useMemo(
    () => extractCategoryInfoFromBreadcrumbs(apiProduct),
    [apiProduct],
  );

  const resolvedBrand = useMemo(() => {
    if (!apiProduct) return null;
    if (apiProduct.brand && typeof apiProduct.brand === "object") {
      return apiProduct.brand;
    }
    return null;
  }, [apiProduct]);

  const breadcrumb = useMemo(() => {
    // Use server-resolved breadcrumbs (BreadcrumbResponse) when available.
    const crumbs = Array.isArray(apiProduct?.breadcrumbs)
      ? apiProduct.breadcrumbs
      : [];

    const items = [];
    // Always prepend a root chip that links to /catalog for easy navigation.
    items.push({ label: "Одежда, обувь и аксессуары", slug: null, root: true });

    for (const c of crumbs) {
      const label =
        c?.label ??
        (c?.labelI18N && typeof c.labelI18N === "object"
          ? c.labelI18N.ru || c.labelI18N.en
          : "") ??
        "";
      if (!label) continue;
      items.push({ label: String(label), slug: c?.slug || null });
    }

    // Brand chip at the end (not a breadcrumb per se, but matches the current UI).
    const brand =
      resolvedBrand?.name ??
      (apiProduct?.brand_name ? String(apiProduct.brand_name) : "");
    if (brand) items.push({ label: String(brand), slug: null, isBrand: true });

    return items;
  }, [apiProduct, resolvedBrand]);

  const infoCards = [
    { title: "Наша\n команда", icon: "/img/FriendsSection1.webp", href: "https://teletype.in/@loyaltymarket/our-team" },
    { title: "Оплата\n и сплит", icon: "/img/brokenPrice.webp", href: "https://teletype.in/@loyaltymarket/payment-and-split" },
    { title: "Доставка \nи отслеживание", icon: "/img/FriendsSection3.webp", href: "https://teletype.in/@loyaltymarket/delivery-and-tracking" },
    { title: "Условия\nвозврата", icon: "/img/FriendsSection4.webp", href: "https://teletype.in/@loyaltymarket/terms-of-return" },
    { title: "Гарантии\n и безопасность", icon: "/img/FriendsSection5.webp", href: "https://teletype.in/@loyaltymarket/guarantees-and-security" },
    {
      title: "POIZON –\n только\n оригинал",
      icon: "/img/FriendsSection6.webp",
      href: "https://teletype.in/@loyaltymarket/poizon-only-original",
    },
    { title: "Подарочные\nкарты", icon: "/img/FriendsSection7.webp", href: "https://teletype.in/@loyaltymarket/gift-cards" },
    { title: "Чат\nс поддержкой", icon: "/img/FriendsSection8.webp" },
  ];

  const recommendedTabs = ["Для вас", "Похожие"];
  const [recommendedTab, setRecommendedTab] = useState(recommendedTabs[0]);

  const skuOptions = useMemo(() => buildSkuOptions(apiProduct), [apiProduct]);

  // Derive the "current" SKU id directly from state + product data so we don't
  // need a setState inside an effect (which would cause cascading renders).
  const resolvedSkuId = useMemo(() => {
    if (selectedSkuId != null) {
      // Ensure it's still in the product; otherwise fall through to default.
      const exists = skuOptions.some(
        (o) => String(o.id) === String(selectedSkuId),
      );
      if (exists) return selectedSkuId;
    }
    return (
      apiProduct?.defaultSku?.id ||
      skuOptions.find((o) => o.isAvailable)?.id ||
      skuOptions[0]?.id ||
      null
    );
  }, [apiProduct, skuOptions, selectedSkuId]);

  const selectedSku = useMemo(() => {
    const skus = Array.isArray(apiProduct?.skus) ? apiProduct.skus : [];
    return skus.find((s) => String(s.id) === String(resolvedSkuId)) || null;
  }, [apiProduct, resolvedSkuId]);

  const effectivePrice =
    (selectedSku?.resolvedPrice ?? selectedSku?.price ?? apiProduct?.price) ??
    null;
  const effectiveCompareAt =
    selectedSku?.compareAtPrice ?? apiProduct?.oldPrice ?? null;

  const needForYou = recommendedTab === "Для вас";
  const needSimilar = recommendedTab === "Похожие";

  // Dedicated PDP placement endpoints — return StorefrontProductCardResponse[]
  // (with images), no category_id required. Uses slug, matches OpenAPI spec.
  const {
    data: forYouRaw,
    isFetching: isForYouFetching,
    isLoading: isForYouLoading,
  } = useGetForYouFeedQuery(
    { limit: 12 },
    { skip: !needForYou },
  );

  const {
    data: similarRaw,
    isFetching: isSimilarFetching,
    isLoading: isSimilarLoading,
  } = useGetSimilarProductsQuery(
    { slug, limit: 12 },
    { skip: !needSimilar || !slug },
  );

  const forYouProducts = useMemo(() => {
    const list = extractProductsList(forYouRaw);
    return list
      .filter((p) => String(p?.id) !== String(productIdNum))
      .map((p) => mapProductCard(p, null))
      .filter(Boolean)
      .slice(0, 12);
  }, [forYouRaw, productIdNum]);

  const similarProducts = useMemo(() => {
    const list = extractProductsList(similarRaw);
    return list
      .filter((p) => String(p?.id) !== String(productIdNum))
      .map((p) => mapProductCard(p, null))
      .filter(Boolean)
      .slice(0, 12);
  }, [productIdNum, similarRaw]);

  const recommendedProducts =
    recommendedTab === "Для вас" ? forYouProducts : similarProducts;
  const isRecommendedLoading =
    recommendedTab === "Для вас"
      ? Boolean(isForYouLoading || isForYouFetching)
      : Boolean(isSimilarLoading || isSimilarFetching);

  const brandsCarousel = useMemo(() => {
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
    // Use brand UUID for precise filter; fallback to name search
    const href = b?.id
      ? `/?brand_id=${encodeURIComponent(String(b.id))}`
      : q
        ? `/search?query=${encodeURIComponent(q)}`
        : "#";

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

  // Backend Reviews moduli yo'q (Spec §11) — PDP review bloki hozircha
  // commented out. Modul tayyor bo'lganda `useProductReviewsQuery(slug)`'ga
  // ulanadi va shu yerga shape moslashadi.

  const handleBuyNow = async (requestedQty) => {
    if (productIdNum == null) return;
    const qty = Math.max(1, Math.min(99, Math.floor(Number(requestedQty) || 1)));
    const skuId = selectedSku?.id ?? resolvedSkuId ?? apiProduct?.defaultSku?.id;

    try {
      const image =
        getProductPhotoCandidates(apiProduct)[0] ?? productImages?.[0] ?? "";
      const meta = {
        image,
        size: selectedSku?.skuCode ?? "",
        skuId: skuId ?? "",
        shippingText: apiProduct?.delivery
          ? `Доставка из ${apiProduct.delivery} до РФ 0₽`
          : "",
        deliveryText: buildDeliveryTextFromProduct(apiProduct),
        article: String(
          selectedSku?.skuCode ??
            apiProduct?.defaultSku?.skuCode ??
            apiProduct?.id ??
            "",
        ),
      };
      const key = "loyaltymarket_cart_meta_v1";
      const existingRaw = localStorage.getItem(key);
      const existing = existingRaw ? JSON.parse(existingRaw) : {};
      const map = existing && typeof existing === "object" ? existing : {};
      map[String(productIdNum)] = meta;
      localStorage.setItem(key, JSON.stringify(map));
      window.dispatchEvent(new Event("loyaltymarket_cart_meta_updated"));
    } catch {
      // ignore
    }

    if (!skuId) {
      console.error("Не удалось купить: не выбран вариант товара");
      return;
    }

    try {
      await addCartItem({ skuId, quantity: qty }).unwrap();
    } catch (e) {
      console.error("Не удалось добавить в корзину", e);
      return;
    }
    router.push("/trash");
  };

  const copyText = async (text) => {
    const value = String(text);

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

  const handleShare = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    const title = productName || "Товар";
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ title, url });
        return;
      } catch {
        // user cancelled or not supported
      }
    }
    await copyText(url);
  };

  const handleCopy = async (text) => {
    const ok = await copyText(text);
    if (!ok) return;
    setIsArticleCopied(true);
    window.setTimeout(() => setIsArticleCopied(false), 1200);
  };

  // Fetch xatolik berdi → not-found ga yo'naltirish
  if (!apiProduct && isProductError) {
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

  // Ma'lumot yuklanyapti — loading.jsx Suspense fallback ko'rsatadi
  if (!apiProduct && isProductLoading) {
    return null;
  }

  if (!apiProduct) {
    return null;
  }

  const productName = apiProduct?.name ?? "";
  const brandName =
    resolvedBrand?.name ??
    (apiProduct?.brand_name ? String(apiProduct.brand_name) : "");
  const priceText = formatRub(apiProduct?.price);

  const brandQuery = String(brandName || "").trim();
  const brandSearchLink = brandQuery
    ? `/search?query=${encodeURIComponent(brandQuery)}`
    : "";

  return (
    <main className={cx("tg-viewport", styles.c1, styles.tw1)}>
      <Container>
        <section className={styles.hero}>
          <ProductImageGallery
            images={productImages}
            productName={productName}
            isFavorite={isFavorite}
            onToggleFavorite={() => toggleFavorite(productIdNum)}
            onShare={handleShare}
            currentImageIndex={currentImageIndex}
            onImageChange={setCurrentImageIndex}
            priorityFirst
          />

          <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
            <div className={cx(styles.breadcrumbRow, "scrollbar-hide")}>
              {breadcrumb.map((crumb, idx) => {
                const isLast = idx === breadcrumb.length - 1;
                const handleBreadcrumbClick = () => {
                  if (isLast) return;
                  if (crumb.isBrand) {
                    const q = String(crumb.label || "").trim();
                    if (q) router.push(`/search?query=${encodeURIComponent(q)}`);
                    return;
                  }
                  if (crumb.root || !crumb.slug) {
                    router.push("/catalog");
                    return;
                  }
                  // Build cumulative slug path for /catalog/<a>/<b>/...
                  const slugs = breadcrumb
                    .slice(0, idx + 1)
                    .filter((c) => !c.root && !c.isBrand && c.slug)
                    .map((c) => c.slug);
                  if (slugs.length) {
                    router.push(`/catalog/${slugs.join("/")}`);
                  } else {
                    router.push("/catalog");
                  }
                };
                return (
                  <button
                    key={`${crumb.label}-${idx}`}
                    type="button"
                    aria-current={isLast ? "page" : undefined}
                    className={cx(
                      styles.breadcrumbChip,
                      isLast && styles.breadcrumbChipActive,
                    )}
                    onClick={handleBreadcrumbClick}
                  >
                    <span className={styles.breadcrumbChipText}>
                      {crumb.label}
                    </span>
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

          <ProductInfo
            productName={productName}
            brand={brandName}
            brandLink={brandSearchLink}
            variants={variants}
            allMedia={allMediaAssets}
            selectedVariantId={resolvedVariantId}
            onVariantChange={(variantId) => {
              setSelectedVariantId(variantId);
              setCurrentImageIndex(0);
            }}
            theme="light"
          />

          {sizeOptions.length > 0 ? (
            <ProductSizes
              sizes={sizeOptions.map((s) => s.label)}
              availableSizes={sizeOptions
                .filter((s) => s.available)
                .map((s) => s.label)}
              onSizeSelect={(label) => {
                const opt = sizeOptions.find((s) => s.label === label);
                if (opt) setSelectedSkuId(opt.skuId ?? null);
              }}
              sizeGuideUrl={sizeGuideUrl}
            />
          ) : skuOptions.length > 1 ? (
            <ProductSkuSelector
              options={skuOptions}
              selectedId={resolvedSkuId}
              onSelect={(opt) => setSelectedSkuId(opt.id)}
              title="Вариант"
            />
          ) : null}
        </section>

        <ProductPrice
          price={formatRub(effectivePrice)}
          deliveryInfo={
            apiProduct?.delivery
              ? `Доставка из ${apiProduct.delivery} до РФ 0₽`
              : ""
          }
          compareAt={effectiveCompareAt}
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

        {/* TODO: InfoCards grid — to be wired when split/info design ready
        <section className={styles.cardsOuter}>
          <div className={cx(styles.cardsRow, "scrollbar-hide")}>
            {infoCards.map((c, index) => (
              <div key={c.title} className={styles.cardItem}>
                {c.href ? (
                  <div
                    role="button"
                    tabIndex={0}
                    style={{
                      textDecoration: "none",
                      color: "inherit",
                      cursor: "pointer",
                      WebkitTapHighlightColor: "transparent",
                    }}
                    onClick={() => {
                      const tg =
                        typeof window !== "undefined" &&
                        window.Telegram?.WebApp;
                      if (tg?.openLink) {
                        tg.openLink(c.href, { try_instant_view: true });
                      } else {
                        window.open(c.href, "_blank", "noopener");
                      }
                    }}
                  >
                    <InfoCard title={c.title} iconSrc={c.icon} index={index} />
                  </div>
                ) : (
                  <InfoCard title={c.title} iconSrc={c.icon} index={index} />
                )}
              </div>
            ))}
          </div>
        </section>
        */}

        {/* Reviews backend moduli tayyor bo'lganda <ProductReviews /> shu yerga
            ulanadi — hozir Spec §11 bo'yicha endpoint mavjud emas. */}

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
                    {selectedSku?.skuCode ??
                      apiProduct?.defaultSku?.skuCode ??
                      (apiProduct?.id != null ? String(apiProduct.id) : "—")}
                  </span>
                  <button
                    type="button"
                    className={styles.copyBtn}
                    aria-label="Скопировать артикул"
                    onClick={() =>
                      handleCopy(
                        selectedSku?.skuCode ??
                          apiProduct?.defaultSku?.skuCode ??
                          apiProduct?.id ??
                          "",
                      )
                    }
                  >
                    {isArticleCopied ? (
                      /* CheckIcon — copied feedback */
                      <svg
                        viewBox="0 0 24 24"
                        width="18"
                        height="18"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                        style={{ color: "#22c55e" }}
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      /* CopyIcon — default */
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
                    )}
                  </button>
                </span>
              </span>
            </div>

            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Категория
                <p></p>
              </span>
              <span className={styles.aboutVal}>
                {resolvedCategory?.label ?? resolvedCategory?.name ?? "—"}
              </span>
            </div>

            <div className={styles.aboutRow}>
              <span className={styles.aboutKey}>
                Тип
                <p></p>
              </span>
              <span className={styles.aboutVal}>
                {resolvedType?.label ?? resolvedType?.name ?? "—"}
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
          favoriteItemIds={favoriteItemIds}
          layout="grid"
          headerVariant="tabs"
          tabs={recommendedTabs}
          activeTab={recommendedTab}
          onTabChange={setRecommendedTab}
          isLoading={isRecommendedLoading}
          onToggleFavorite={toggleFavorite}
        />

        <ProductAddToCart onBuyNow={handleBuyNow} />
      </Container>
      <Footer />
    </main>
  );
}
