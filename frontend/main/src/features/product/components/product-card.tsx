"use client";

import { memo, useCallback, useMemo } from "react";

import { useRouter } from "next/navigation";

import { Heart, Plus } from "lucide-react";

import { ImgWithFallback } from "@/components/ui/img-with-fallback";
import { formatSplitPayment } from "@/lib/format";
import { getProductPhotoCandidates } from "@/lib/format/product-image";
import { cn } from "@/lib/utils";
import type { ProductCardData } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ProductCardVariant = "normal" | "compact";

export interface ProductCardProps {
  product: ProductCardData;
  variant?: ProductCardVariant;
  /** Set of favorite product IDs (external source of truth) */
  favoriteItemIds?: Set<number | string>;
  onToggleFavorite: (productId: number | string) => void;
  hideFavoriteButton?: boolean;
  isPurchased?: boolean;
  isViewed?: boolean;
  onQuickAdd?: (productId: number | string) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildInstallmentText(product: ProductCardData): string {
  if (product.installment?.trim()) {
    return product.installment.trim();
  }

  const digits = String(product.price ?? "").replace(/[^0-9]/g, "");
  if (!digits) return "";

  const total = Number(digits);
  if (!Number.isFinite(total) || total <= 0) return "";

  const perMonth = formatSplitPayment(total, 4);
  const formatted = perMonth.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `4 \u00d7 ${formatted} \u20bd \u0432 \u0441\u043f\u043b\u0438\u0442`;
}

function splitInstallment(text: string) {
  const rubIdx = text.indexOf("\u20bd");
  if (rubIdx === -1) return { pricePart: text, splitPart: "" };
  return {
    pricePart: text.slice(0, rubIdx + 1),
    splitPart: text.slice(rubIdx + 1).trim(),
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const ProductCard = memo(function ProductCard({
  product,
  variant = "normal",
  favoriteItemIds,
  onToggleFavorite,
  hideFavoriteButton = false,
  isPurchased = false,
  isViewed = false,
  onQuickAdd,
}: ProductCardProps) {
  const router = useRouter();
  const isCompact = variant === "compact";

  const isFavorite = favoriteItemIds
    ? favoriteItemIds.has(product.id)
    : Boolean(product.isFavorite);

  // Image sources via the shared candidate builder
  const imageSources = useMemo(
    () => getProductPhotoCandidates(product),
    [product],
  );

  // Fallback letter when all images fail
  const fallbackLetter = useMemo(() => {
    const name = product.name?.trim() ?? "";
    return name ? name.slice(0, 1).toUpperCase() : "";
  }, [product.name]);

  // Installment / split payment text
  const installmentText = useMemo(() => buildInstallmentText(product), [product]);
  const { pricePart, splitPart } = useMemo(
    () => splitInstallment(installmentText),
    [installmentText],
  );

  const deliveryLabel =
    product.deliveryDate?.trim() ||
    product.deliveryText?.trim() ||
    "\u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430";

  // Handlers
  const openProduct = useCallback(() => {
    if (!product.id) return;
    router.push(`/product/${product.id}`);
  }, [product.id, router]);

  const handleFavoriteClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onToggleFavorite(product.id);
    },
    [onToggleFavorite, product.id],
  );

  const handleQuickAdd = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onQuickAdd?.(product.id);
    },
    [onQuickAdd, product.id],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openProduct();
      }
    },
    [openProduct],
  );

  return (
    <div
      className={cn(
        "flex w-full flex-none cursor-pointer flex-col",
        isCompact && "h-full max-w-[143px]",
      )}
      onClick={openProduct}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* ---- Image area ---- */}
      <div
        className={cn(
          "relative overflow-hidden rounded-2xl bg-[#f4f3f1]",
          isCompact ? "mb-[15px] h-[191px]" : "mb-[5px] h-[239px]",
        )}
      >
        {/* Centered image / fallback */}
        <div className="absolute inset-0 flex items-center justify-center p-[5px] pb-0">
          {imageSources.length > 0 ? (
            <ImgWithFallback
              sources={imageSources}
              alt={product.name ?? ""}
              className="h-full w-full scale-110 object-contain"
              fallbackElement={
                <span className="text-4xl font-semibold text-neutral-400">
                  {fallbackLetter}
                </span>
              }
            />
          ) : (
            <span className="text-4xl font-semibold text-neutral-400">
              {fallbackLetter}
            </span>
          )}
        </div>

        {/* Favorite button */}
        {!hideFavoriteButton && (
          <button
            type="button"
            className="absolute right-1.5 top-1.5 flex h-[22px] w-[24px] cursor-pointer items-center justify-center rounded-full border-0 bg-transparent"
            aria-pressed={isFavorite}
            aria-label={isFavorite ? "Убрать из избранного" : "Добавить в избранное"}
            onClick={handleFavoriteClick}
          >
            <Heart
              className={cn(
                "h-[19px] w-[20px]",
                isFavorite
                  ? "fill-red-500 stroke-red-500"
                  : "fill-none stroke-neutral-500",
              )}
              strokeWidth={1.8}
            />
          </button>
        )}
      </div>

      {/* Slider dots (normal variant only) */}
      {variant === "normal" && (
        <img
          className="mx-auto my-1.5 block opacity-65"
          src="/icons/product/dots-mini-slider.svg"
          alt=""
          aria-hidden="true"
        />
      )}

      {/* ---- Meta: price, installment, name ---- */}
      <div className="pl-0">
        <div
          className={cn(
            "mb-0.5 font-semibold leading-none text-black",
            isCompact ? "text-base" : "text-xl",
          )}
        >
          {product.price}
        </div>

        {installmentText && (isViewed || isPurchased) && (
          <div className="mt-1.5 flex text-xs font-semibold leading-[1.2] text-black">
            <span>{pricePart}</span>
            &nbsp;
            <span className="font-normal">{splitPart}</span>
          </div>
        )}

        {product.brand && (
          <div className="mt-1 text-xs leading-[1.2] text-neutral-500">
            {product.brand}
          </div>
        )}

        <div className="mt-1.5 line-clamp-2 min-h-[28px] text-xs font-medium leading-[1.2] text-black">
          {product.name}
        </div>
      </div>

      {/* ---- Delivery / Quick Add button ---- */}
      {!isPurchased && (
        <button
          type="button"
          className="mt-2.5 flex h-10 w-full items-center justify-center rounded-2xl border-0 bg-[#f4f3f1] transition-colors active:bg-[#e9e8e5]"
          onClick={handleQuickAdd}
        >
          <Plus className="mr-1.5 h-4 w-4 text-black" strokeWidth={2} />
          <span className="text-[13px] font-semibold leading-[1.06] tracking-[0.02em] text-black">
            {deliveryLabel}
          </span>
        </button>
      )}
    </div>
  );
},
// Custom comparator for list performance
(prev, next) => {
  if (prev.product !== next.product) return false;
  if (prev.variant !== next.variant) return false;
  if (prev.hideFavoriteButton !== next.hideFavoriteButton) return false;
  if (prev.isPurchased !== next.isPurchased) return false;
  if (prev.isViewed !== next.isViewed) return false;
  if (prev.onToggleFavorite !== next.onToggleFavorite) return false;
  if (prev.onQuickAdd !== next.onQuickAdd) return false;

  // Only re-render if THIS card's favorite status actually changed
  const prevFav = prev.favoriteItemIds
    ? prev.favoriteItemIds.has(prev.product.id)
    : Boolean(prev.product.isFavorite);
  const nextFav = next.favoriteItemIds
    ? next.favoriteItemIds.has(next.product.id)
    : Boolean(next.product.isFavorite);
  if (prevFav !== nextFav) return false;

  return true;
});
