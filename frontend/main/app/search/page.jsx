"use client";
const EMPTY_SET = new Set();

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  Suspense,
} from "react";
import { useSearchParams } from "next/navigation";
import { Search, Trash2 } from "lucide-react";

import Footer from "@/components/layout/Footer";
import Container from "@/components/layout/Layout";
import ProductSection from "@/components/blocks/product/ProductSection";
import SearchBar from "@/components/blocks/search/SearchBar";
import SelectSheet from "@/components/blocks/search/SelectSheet";
import PriceSheet from "@/components/blocks/search/PriceSheet";
import FiltersSheet from "@/components/blocks/search/FiltersSheet";
import { cn } from "@/lib/format/cn";

import {
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "@/lib/format/backendAssets";

import styles from "./page.module.css";

function SearchPageContent() {
  const inputRef = useRef(null);
  const searchParams = useSearchParams();
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [hasTyped, setHasTyped] = useState(false);
  const blurCloseTimerRef = useRef(null);
  const [historyCleared, setHistoryCleared] = useState(false);

  const [debouncedQuery, setDebouncedQuery] = useState("");

  const normalize = useCallback(
    (value) =>
      String(value || "")
        .trim()
        .replace(/\s+/g, " ")
        .toLowerCase(),
    [],
  );

  const [sortOpen, setSortOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [typeOpen, setTypeOpen] = useState(false);
  const [brandOpen, setBrandOpen] = useState(false);
  const [priceOpen, setPriceOpen] = useState(false);

  const reopenFiltersAfterPickerRef = useRef(false);

  const [sort, setSort] = useState("popular");
  const [categoryId, setCategoryId] = useState(null);
  const [typeIds, setTypeIds] = useState([]);
  const [brandIds, setBrandIds] = useState([]);
  const [priceRange, setPriceRange] = useState({ min: null, max: null });

  const [delivery, setDelivery] = useState({
    inStock: false,
    fromChina: false,
  });
  const [original, setOriginal] = useState(false);

  const favoriteItemIds = EMPTY_SET;
  const toggleFavorite = () => {};
  const onToggleFavorite = useCallback(
    (id) => toggleFavorite(id),
    [toggleFavorite],
  );
  const [baseProducts, setBaseProducts] = useState([]);
  const [isProductsLoading, setIsProductsLoading] = useState(false);

  const searchHistoryRaw = [];
  const isHistoryLoading = false;
  const isHistoryFetching = false;

  const createSearchHistory = () => {};

  const suggestRaw = [];
  const isSuggestLoading = false;
  const isSuggestFetching = false;

  useEffect(() => {
    const frame = requestAnimationFrame(() => inputRef.current?.focus?.());
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const paramQuery = searchParams.get("query");
    if (paramQuery != null) {
      setQuery(paramQuery);
      setSubmittedQuery(paramQuery);
      setHasTyped(false);
    }
  }, [searchParams]);

  const showSuggestions = isFocused && hasTyped && normalize(query).length > 0;
  const showResults = !showSuggestions && normalize(submittedQuery).length > 0;

  useEffect(() => {
    if (!showSuggestions) {
      setDebouncedQuery("");
      return;
    }

    const next = String(query || "");
    const t = window.setTimeout(() => {
      setDebouncedQuery(next);
    }, 220);
    return () => window.clearTimeout(t);
  }, [query, showSuggestions]);

  const serverSuggestions = useMemo(() => {
    if (!Array.isArray(suggestRaw)) return [];
    return suggestRaw
      .map((x) => String(x || "").trim())
      .filter(Boolean)
      .slice(0, 20);
  }, [suggestRaw]);

  const recent = useMemo(() => {
    if (historyCleared) return [];
    const rows = Array.isArray(searchHistoryRaw) ? searchHistoryRaw : [];
    const byDate = [...rows].sort((a, b) => {
      const ad =
        typeof a?.searched_at === "string" ? Date.parse(a.searched_at) : 0;
      const bd =
        typeof b?.searched_at === "string" ? Date.parse(b.searched_at) : 0;
      return (Number.isFinite(bd) ? bd : 0) - (Number.isFinite(ad) ? ad : 0);
    });

    const seen = new Set();
    const out = [];
    for (const it of byDate) {
      const label = String(it?.query ?? "").trim();
      if (!label) continue;
      const key = normalize(label);
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(label);
      if (out.length >= 12) break;
    }
    return out;
  }, [historyCleared, normalize, searchHistoryRaw]);

  const suggestions = useMemo(() => {
    // Show only backend suggestions while typing.
    return Array.isArray(serverSuggestions)
      ? serverSuggestions.slice(0, 12)
      : [];
  }, [serverSuggestions]);

  const showSuggestSkeleton =
    showSuggestions &&
    (isSuggestLoading || isSuggestFetching) &&
    (!Array.isArray(suggestions) || suggestions.length === 0);

  const showRecentSkeleton =
    !query &&
    !historyCleared &&
    (isHistoryLoading || isHistoryFetching) &&
    (!Array.isArray(recent) || recent.length === 0);

  const SuggestSkeleton = () => {
    const widths = [78, 64, 86, 58, 72, 90];
    return (
      <div className={styles.skelSuggestList} aria-hidden="true">
        {widths.map((w, idx) => (
          <div key={idx} className={styles.skelSuggestItem}>
            <span className={styles.skelSuggestIcon} />
            <span
              className={styles.skelSuggestLine}
              style={{ width: `${w}%` }}
            />
          </div>
        ))}
      </div>
    );
  };

  const RecentSkeleton = () => {
    const widths = [92, 70, 84, 60, 78, 66];
    return (
      <div className={styles.skelChips} aria-hidden="true">
        {widths.map((w, idx) => (
          <span
            key={idx}
            className={styles.skelChip}
            style={{ width: `${w}px` }}
          />
        ))}
      </div>
    );
  };

  const priceToNumber = (value) => {
    const n = Number(String(value || "").replace(/[^0-9]/g, ""));
    return Number.isFinite(n) ? n : 0;
  };

  const categoriesData = [];
  const categoriesWithTypesData = [];
  const brandsData = [];

  const categories = useMemo(() => {
    if (!Array.isArray(categoriesData)) return [];
    return categoriesData
      .filter((c) => c && typeof c === "object")
      .map((c) => ({ id: c.id, name: c.name ?? c.title ?? c.label ?? "" }))
      .filter((c) => c.id != null && String(c.name).trim());
  }, [categoriesData]);

  const categoryOptions = useMemo(() => {
    const values = [...categories].sort((a, b) =>
      String(a.name).localeCompare(String(b.name)),
    );
    return [

      ...values.map((c) => ({ value: c.id, label: c.name })),
    ];
  }, [categories]);

  const typeOptions = useMemo(() => {
    if (!categoriesWithTypesData) return [];

    const items = [];

    const pushCategory = (label, types) => {
      if (!label) return;
      items.push({ kind: "section", label: String(label).toUpperCase() });
      for (const t of types) {
        if (!t || typeof t !== "object") continue;
        const id = t.id;
        const name = t.name ?? t.title ?? t.label ?? "";
        if (id == null || !String(name).trim()) continue;
        items.push({ value: id, label: String(name) });
      }
    };

    // Supported shapes:
    // 1) [{id,name,types:[{id,name}]}]
    // 2) {items:[...]}
    const root = Array.isArray(categoriesWithTypesData)
      ? categoriesWithTypesData
      : Array.isArray(categoriesWithTypesData?.items)
        ? categoriesWithTypesData.items
        : [];

    for (const c of root) {
      if (!c || typeof c !== "object") continue;
      const label = c.name ?? c.title ?? c.label ?? "";
      const types = Array.isArray(c.types) ? c.types : [];
      pushCategory(label, types);
    }

    return items;
  }, [categoriesWithTypesData]);

  const brandsList = useMemo(() => {
    if (!Array.isArray(brandsData)) return [];
    return brandsData
      .filter((b) => b && typeof b === "object")
      .map((b) => ({ id: b.id, name: b.name ?? b.title ?? b.label ?? "" }))
      .filter((b) => b.id != null && String(b.name).trim());
  }, [brandsData]);

  const brandOptions = useMemo(() => {
    const values = [...brandsList].sort((a, b) =>
      String(a.name).localeCompare(String(b.name)),
    );
    return values.map((b) => ({ value: b.id, label: b.name }));
  }, [brandsList]);

  const categoryLabel = useMemo(() => {
    if (categoryId == null) return null;
    const hit = categories.find((c) => String(c.id) === String(categoryId));
    return hit?.name ?? String(categoryId);
  }, [categories, categoryId]);

  const formatNum = (n) => (n == null ? "" : Number(n).toLocaleString("ru-RU"));

  const priceLabel = useMemo(() => {
    const min = priceRange?.min ?? null;
    const max = priceRange?.max ?? null;
    if (min == null && max == null) return "Цена";
    if (min != null && max != null)
      return `${formatNum(min)}–${formatNum(max)} ₽`;
    if (min != null) return `От ${formatNum(min)} ₽`;
    return `До ${formatNum(max)} ₽`;
  }, [priceRange?.max, priceRange?.min]);

  const brandIdToName = useMemo(() => {
    const m = new Map();
    for (const b of brandsList) m.set(String(b.id), String(b.name));
    return m;
  }, [brandsList]);

  const typeIdToName = useMemo(() => {
    const m = new Map();
    const collect = (arr) => {
      for (const it of arr) {
        if (!it || typeof it !== "object") continue;
        if (it.kind === "section") continue;
        if (it.value == null) continue;
        m.set(String(it.value), String(it.label ?? it.value));
      }
    };
    collect(typeOptions);
    return m;
  }, [typeOptions]);

  const brandChipLabel = useMemo(() => {
    if (!brandIds?.length) return "Бренд";
    const first = brandIdToName.get(String(brandIds[0])) ?? String(brandIds[0]);
    if (brandIds.length === 1) return first;
    return `${first} +${brandIds.length - 1}`;
  }, [brandIdToName, brandIds]);

  const typeChipLabel = useMemo(() => {
    if (!typeIds?.length) return "Тип";
    const first = typeIdToName.get(String(typeIds[0])) ?? String(typeIds[0]);
    if (typeIds.length === 1) return first;
    return `${first} +${typeIds.length - 1}`;
  }, [typeIdToName, typeIds]);

  const commitSearch = (value) => {
    const next = String(value || "").trim();
    if (!next) return;

    if (blurCloseTimerRef.current) {
      window.clearTimeout(blurCloseTimerRef.current);
      blurCloseTimerRef.current = null;
    }
    setIsFocused(false);
    setHasTyped(false);
    setHistoryCleared(false);

    setQuery(next);
    setSubmittedQuery(next);

    // Persist into backend history (best-effort)
    try {
      const parameters = {
        sort,
        category_id: categoryId,
        type_ids: Array.isArray(typeIds) ? typeIds : [],
        brand_ids: Array.isArray(brandIds) ? brandIds : [],
        price_min: priceRange?.min ?? null,
        price_max: priceRange?.max ?? null,
        delivery,
        original,
      };
      createSearchHistory({ query: next, parameters });
    } catch {
      // ignore
    }
  };

  const renderSuggestionLabel = (label) => {
    const q = normalize(query);
    const hay = label;
    const hayLower = hay.toLowerCase();
    const idx = q ? hayLower.indexOf(q) : -1;
    if (idx < 0 || !q)
      return <span className={styles.suggestText}>{label}</span>;

    const before = hay.slice(0, idx);
    const match = hay.slice(idx, idx + q.length);
    const after = hay.slice(idx + q.length);

    return (
      <span className={styles.suggestText}>
        {before}
        <span className={styles.suggestStrong}>{match}</span>
        <span className={styles.suggestRest}>{after}</span>
      </span>
    );
  };

  // onToggleFavorite is memoized above

  const searchKey = useMemo(() => {
    const q = normalize(submittedQuery);
    if (!q) return null;
    return JSON.stringify({
      q,
      categoryId,
      typeId: Array.isArray(typeIds) && typeIds.length ? typeIds[0] : null,
      brandId: Array.isArray(brandIds) && brandIds.length ? brandIds[0] : null,
      priceMin: priceRange?.min ?? null,
      priceMax: priceRange?.max ?? null,
    });
  }, [
    brandIds,
    categoryId,
    normalize,
    priceRange?.max,
    priceRange?.min,
    submittedQuery,
    typeIds,
  ]);

  const formatPrice = useCallback((value) => {
    if (value == null) return "";
    if (typeof value === "string") {
      const s = value.trim();
      if (!s) return "";
      return /₽/.test(s) ? s : `${s} ₽`;
    }
    const n = Number(value);
    if (!Number.isFinite(n)) return "";
    return `${Math.trunc(n).toLocaleString("ru-RU")} ₽`;
  }, []);

  const getProductPhotoCandidates = useCallback((product) => {
    const candidates = [];

    const rawDirect =
      (typeof product?.image === "string" ? product.image : "") ||
      (typeof product?.image_url === "string" ? product.image_url : "") ||
      (typeof product?.photo === "string" ? product.photo : "") ||
      (typeof product?.photo_url === "string" ? product.photo_url : "");
    if (rawDirect && rawDirect.trim()) candidates.push(rawDirect.trim());

    const images = Array.isArray(product?.images) ? product.images : [];
    const first = images?.[0];
    const fromImages =
      typeof first === "string"
        ? first
        : first && typeof first === "object"
          ? (first.filename ?? first.file ?? first.path ?? first.url)
          : null;
    const raw = typeof fromImages === "string" ? fromImages.trim() : "";
    if (raw) candidates.push(raw);

    // Home page uses `photos[0].filename`; search results often come in the same shape.
    const photos = Array.isArray(product?.photos) ? product.photos : [];
    const firstPhoto = photos?.[0];
    const fromPhotos =
      typeof firstPhoto === "string"
        ? firstPhoto
        : firstPhoto && typeof firstPhoto === "object"
          ? (firstPhoto.filename ??
            firstPhoto.file ??
            firstPhoto.path ??
            firstPhoto.url)
          : null;
    const rawPhoto = typeof fromPhotos === "string" ? fromPhotos.trim() : "";
    if (rawPhoto) candidates.push(rawPhoto);

    const uniq = Array.from(
      new Set(candidates.filter((x) => typeof x === "string" && x.trim())),
    );

    const out = [];
    for (const src of uniq) {
      out.push(
        buildProductPhotoUrl(src),
        buildBackendAssetUrl(src, ["media"]),
        buildBackendAssetUrl(src, ["static"]),
        buildBackendAssetUrl(src, ["uploads"]),
        buildBackendAssetUrl(src),
      );
    }

    return out.filter((x) => typeof x === "string" && x.trim());
  }, []);

  const mapProductToUiBase = useCallback(
    (p) => {
      if (!p || typeof p !== "object") return null;
      const id = p.id;
      if (id == null) return null;

      const name = p.name ?? p.title ?? p.product_name ?? p.model ?? "";

      const candidates = getProductPhotoCandidates(p);
      const image = candidates[0] ?? "";
      const imageFallbacks = candidates.slice(1);

      const brandName =
        (typeof p.brand === "object" ? p.brand?.name : p.brand) ??
        p.brand_name ??
        "";

      const deliveryDate =
        p.deliveryDate ?? p.delivery_date ?? p.delivery ?? "";

      return {
        id,
        name: String(name || ""),
        price: formatPrice(p.price ?? p.price_rub ?? p.amount ?? ""),
        image: String(image || ""),
        brand: String(brandName || ""),
        deliveryDate: typeof deliveryDate === "string" ? deliveryDate : "",
        serverIsFavorite: Boolean(
          p.isFavorite ?? p.is_favorite ?? p.is_favourite,
        ),
        rating: p.rating,
        installment: p.installment,
        imageFallbacks,
      };
    },
    [formatPrice, getProductPhotoCandidates],
  );

  useEffect(() => {
    setBaseProducts([]);
    setIsProductsLoading(false);
  }, [searchKey, mapProductToUiBase, normalize]);

  const productsForUi = useMemo(() => {
    return baseProducts.map((p) => ({
      ...p,
      isFavorite: Boolean(p.serverIsFavorite || favoriteItemIds.has(p.id)),
    }));
  }, [baseProducts, favoriteItemIds]);

  const priceBounds = useMemo(() => {
    let min = null;
    let max = null;
    for (const p of productsForUi) {
      const price = priceToNumber(p.price);
      if (!price) continue;
      if (min == null || price < min) min = price;
      if (max == null || price > max) max = price;
    }
    return { min, max };
  }, [productsForUi]);

  const filteredProducts = useMemo(() => {
    const q = normalize(submittedQuery);
    if (!q) return [];

    // baseProducts уже собраны по query; оставляем фильтр как safety.
    const base = productsForUi.filter((p) =>
      normalize(`${p?.name ?? ""} ${p?.brand ?? ""}`).includes(q),
    );

    if (sort === "price_asc") {
      return [...base].sort(
        (a, b) => priceToNumber(a.price) - priceToNumber(b.price),
      );
    }

    if (sort === "price_desc") {
      return [...base].sort(
        (a, b) => priceToNumber(b.price) - priceToNumber(a.price),
      );
    }

    return base;
  }, [productsForUi, sort, submittedQuery, normalize]);

  const closeTypeSheet = () => {
    setTypeOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setFiltersOpen(true);
    }
  };

  const closeBrandSheet = () => {
    setBrandOpen(false);
    if (reopenFiltersAfterPickerRef.current) {
      reopenFiltersAfterPickerRef.current = false;
      setFiltersOpen(true);
    }
  };

  const filterCategories = useMemo(() => {
    const set = new Set(["Одежда", "Обувь", "Аксессуары"]);
    for (const opt of categoryOptions) {
      if (opt?.label) set.add(opt.label);
    }
    return Array.from(set).slice(0, 3);
  }, [categoryOptions]);

  const [isSearchActivated, setSearchActivated] = useState(false);

  return (
    <main className={cn("tg-viewport", styles.page)}>
      <Container className={styles.container}>
        <div className={styles.outerWrap}>
          <SearchBar
            isSearchActivated={isSearchActivated}
            isSearchClear={() => {
              setHasTyped(false);
              setQuery("");
              setSearchActivated(false);
            }}
            inputRef={inputRef}
            autoFocus
            // showIcon={false}
            actionLabel="Найти"
            actionAriaLabel="Искать"
            onAction={() => commitSearch(query)}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setHasTyped(true);
              setSearchActivated(true);
            }}
            onFocus={() => {
              if (blurCloseTimerRef.current) {
                window.clearTimeout(blurCloseTimerRef.current);
                blurCloseTimerRef.current = null;
              }
              setIsFocused(true);
              setHasTyped(false);
            }}
            onBlur={() => {
              // Delay closing so clicks on suggestions work.
              blurCloseTimerRef.current = window.setTimeout(() => {
                setIsFocused(false);
                blurCloseTimerRef.current = null;
              }, 150);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                commitSearch(query);
              }
            }}
            inputMode="search"
            enterKeyHint="search"
          />
        </div>

        {showSuggestions ? (
          <div className={styles.suggestWrap}>
            <div
              className={styles.suggestList}
              role="listbox"
              aria-label="Подсказки"
              aria-busy={showSuggestSkeleton ? "true" : "false"}
            >
              {showSuggestSkeleton ? (
                <SuggestSkeleton />
              ) : (
                suggestions.map((label) => (
                  <button
                    key={label}
                    type="button"
                    className={styles.suggestItem}
                    onMouseDown={(e) => {
                      // Prevent input blur before click.
                      e.preventDefault();
                    }}
                    onClick={() => commitSearch(label)}
                    role="option"
                    aria-selected="false"
                  >
                    <span>
                      <Search
                        size={18}
                        className={styles.suggestItemIcon}
                        aria-hidden="true"
                      />
                    </span>
                    {renderSuggestionLabel(label)}
                  </button>
                ))
              )}
            </div>
          </div>
        ) : null}

        {!query ? (
          showRecentSkeleton || (Array.isArray(recent) && recent.length > 0) ? (
            <section className={styles.recent} aria-label="Вы искали">
              <div className={styles.recentHeader}>
                <div className={styles.recentTitle}>Вы искали</div>

                <button
                  type="button"
                  className={styles.trashBtn}
                  aria-label="Очистить историю"
                  onClick={() => setHistoryCleared(true)}
                >
                  <Trash2 size={18} aria-hidden="true" />
                </button>
              </div>

              <div className={styles.chips}>
                {showRecentSkeleton ? (
                  <RecentSkeleton />
                ) : (
                  recent.map((label, idx) => (
                    <button
                      key={`${label}-${idx}`}
                      type="button"
                      className={styles.chip}
                      onClick={() => commitSearch(label)}
                    >
                      {label}
                    </button>
                  ))
                )}
              </div>
            </section>
          ) : null
        ) : (
          <section className={styles.results} aria-label="Результаты">
            {showResults ? (
              <>
                <div className={styles.filtersBar} aria-label="Фильтры">
                  <div className={cn(styles.filtersRow, "scrollbar-hide")}>
                    <button
                      type="button"
                      className={styles.iconChip}
                      aria-label="Сортировка"
                      onClick={() => setSortOpen(true)}
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
                          stroke="black"
                          strokeWidth="1.53178"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                    <button
                      type="button"
                      className={styles.iconChip}
                      aria-label="Фильтры"
                      onClick={() => setFiltersOpen(true)}
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
                          stroke="black"
                          strokeWidth="1.4"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>

                    <button
                      type="button"
                      className={cn(
                        styles.filterChip,
                        categoryId != null ? styles.filterChipActive : null,
                      )}
                      onClick={() => setCategoryOpen(true)}
                    >
                      <span>{categoryLabel || "Категория"}</span>

                      {categoryId != null ? (
                        <span
                          className={styles.selectedChipX}
                          aria-hidden="true"
                        >
                          <img src="/icons/global/markXBlack.svg" alt="" />
                        </span>
                      ) : (
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
                              stroke="#F4F3F1"
                              strokeWidth="0"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </span>
                      )}
                    </button>
                    <button
                      type="button"
                      className={cn(
                        styles.filterChip,
                        typeIds?.length ? styles.filterChipActive : null,
                      )}
                      onClick={() => setTypeOpen(true)}
                    >
                      <span>{typeChipLabel}</span>
                      {typeIds?.length ? (
                        <span
                          className={styles.selectedChipX}
                          aria-hidden="true"
                        >
                          <img src="/icons/global/markXBlack.svg" alt="" />
                        </span>
                      ) : (
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
                              stroke="#000000"
                              strokeWidth="0"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </span>
                      )}
                    </button>
                    <button
                      type="button"
                      className={cn(
                        styles.filterChip,
                        brandIds?.length ? styles.filterChipActive : null,
                      )}
                      onClick={() => setBrandOpen(true)}
                    >
                      <span>{brandChipLabel}</span>
                      {brandIds?.length ? (
                        <span
                          className={styles.selectedChipX}
                          aria-hidden="true"
                        >
                          <img src="/icons/global/markXBlack.svg" alt="" />
                        </span>
                      ) : (
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
                              stroke="#000000"
                              strokeWidth="0"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </span>
                      )}
                    </button>
                    <button
                      type="button"
                      className={cn(
                        styles.filterChip,
                        priceRange?.min != null || priceRange?.max != null
                          ? styles.filterChipActive
                          : null,
                      )}
                      onClick={() => setPriceOpen(true)}
                    >
                      <span>{priceLabel}</span>

                      {priceRange?.min != null || priceRange?.max != null ? (
                        <span
                          className={styles.selectedChipX}
                          aria-hidden="true"
                        >
                          <img src="/icons/global/markXBlack.svg" alt="" />
                        </span>
                      ) : (
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
                              stroke="#000000"
                              strokeWidth="0"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </span>
                      )}
                    </button>
                  </div>
                </div>

                {filteredProducts.length === 0 && !isProductsLoading ? (
                  <div
                    className={styles.empty}
                    role="status"
                    aria-live="polite"
                  >
                    <div className={styles.emptyTitle}>Ничего не найдено</div>
                    <div className={styles.emptySubtitle}>
                      Но можно поискать что-то другое
                    </div>
                  </div>
                ) : (
                  <ProductSection
                    title=""
                    products={filteredProducts}
                    onToggleFavorite={onToggleFavorite}
                    layout="grid"
                    isLoading={isProductsLoading}
                    isViewed={true}
                  />
                )}
              </>
            ) : null}
          </section>
        )}

        {!isFocused ? <Footer /> : null}

        <SelectSheet
          open={sortOpen}
          onClose={() => setSortOpen(false)}
          title="Показывать сначала"
          options={[
            { value: "popular", label: "Популярные" },
            { value: "price_asc", label: "Подешевле" },
            { value: "price_desc", label: "Подороже" },
          ]}
          value={sort}
          onApply={(v) => setSort(v)}
        />

        <SelectSheet
          open={categoryOpen}
          onClose={() => setCategoryOpen(false)}
          title="Категория"
          options={categoryOptions}
          value={categoryId}
          onApply={(v) => setCategoryId(v ?? null)}
        />

        <SelectSheet
          open={typeOpen}
          onClose={closeTypeSheet}
          title="Тип"
          options={typeOptions}
          multiple
          control="check"
          showSelectedChips
          value={typeIds}
          onApply={(v) => setTypeIds(Array.isArray(v) ? v : [])}
          isTypeModule={true}
        />

        <SelectSheet
          open={brandOpen}
          onClose={closeBrandSheet}
          title="Бренд"
          options={brandOptions}
          multiple
          value={brandIds}
          searchable
          searchPlaceholder="Найти бренд"
          groupBy="alpha"
          onApply={(v) => setBrandIds(Array.isArray(v) ? v : [])}
        />

        <PriceSheet
          open={priceOpen}
          onClose={() => setPriceOpen(false)}
          title="Цена"
          value={priceRange}
          minPlaceholder={priceBounds.min}
          maxPlaceholder={priceBounds.max}
          onApply={(v) => setPriceRange(v)}
        />

        <FiltersSheet
          open={filtersOpen}
          onClose={() => setFiltersOpen(false)}
          categories={filterCategories}
          value={{
            category: categoryLabel,
            types: typeIds.map(
              (id) => typeIdToName.get(String(id)) ?? String(id),
            ),
            brands: brandIds.map(
              (id) => brandIdToName.get(String(id)) ?? String(id),
            ),
            priceRange,
            delivery,
            original,
          }}
          priceBounds={priceBounds}
          onApply={(next) => {
            // Пока FiltersSheet работает со строковыми значениями.
            // Сбрасываем selection на "sheet"-уровне через отдельные пикеры.
            if (next.category == null) setCategoryId(null);
            if (Array.isArray(next.types) && next.types.length === 0)
              setTypeIds([]);
            if (Array.isArray(next.brands) && next.brands.length === 0)
              setBrandIds([]);
            setPriceRange(next.priceRange ?? { min: null, max: null });
            setDelivery(next.delivery ?? { inStock: false, fromChina: false });
            setOriginal(Boolean(next.original));
          }}
          onOpenTypePicker={() => {
            reopenFiltersAfterPickerRef.current = true;
            setFiltersOpen(false);
            setTypeOpen(true);
          }}
          onOpenBrandPicker={() => {
            reopenFiltersAfterPickerRef.current = true;
            setFiltersOpen(false);
            setBrandOpen(true);
          }}
        />
      </Container>
    </main>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div>Загрузка...</div>}>
      <SearchPageContent />
    </Suspense>
  );
}
