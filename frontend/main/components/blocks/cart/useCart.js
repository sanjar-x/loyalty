"use client";

import { useCallback, useMemo } from "react";

import {
  useClearCartMutation,
  useGetMyCartQuery,
  useRemoveCartItemMutation,
  useUpdateCartItemMutation,
} from "@/lib/store/api";
import { buildBackendAssetUrl } from "@/lib/format/backendAssets";

/**
 * useCart — thin adapter over RTK Query getMyCart.
 *
 * Backend (OpenAPI):
 *   CartResponse { id, status, itemCount, total: MoneyResponse,
 *                  groups: CartGroupResponse[] }
 *   CartItemResponse { id, skuId, productId, variantId, productName,
 *                      variantLabel, imageUrl, quantity, unitPrice, lineTotal,
 *                      supplierType, addedAt }
 *
 * `getMyCart` transformResponse allaqachon flat shape yasaydi
 * (`lib/store/api.js#normalizeCartResponse`), shu yerda faqat UI-friendly
 * maydonlarni qo'shamiz (deliveryText, shippingText).
 *
 * @typedef {Object} CartItem
 * @property {string} id               backend CartItem.id (UUID)
 * @property {string} skuId            backend SKU UUID (mutatsiyalar uchun)
 * @property {string} productId
 * @property {string} variantId
 * @property {string} name             productName
 * @property {string} variantLabel
 * @property {string} image            imageUrl (proxy'langan)
 * @property {number} priceRub
 * @property {number} lineTotalRub
 * @property {number} quantity
 * @property {string} supplierType     "china" | "retail" | ...
 * @property {string} deliveryText     UI string derived from supplierType
 * @property {string} shippingText     UI string
 * @property {string} addedAt          ISO date
 */
function toUiImage(raw) {
  if (typeof raw !== "string" || !raw.trim()) return "";
  try {
    const absolute = raw.trim().startsWith("http");
    return absolute ? raw.trim() : buildBackendAssetUrl(raw.trim());
  } catch {
    return raw.trim();
  }
}

function supplierToDelivery(supplierType) {
  const key = String(supplierType || "").toLowerCase();
  if (key.includes("china") || key === "cn") return "Из Китая";
  if (key.includes("stock") || key === "retail" || key === "ru")
    return "Из наличия";
  return "";
}

export function useCart() {
  const { data: cart, isLoading, isFetching, isError } = useGetMyCartQuery();

  const [updateCartItem] = useUpdateCartItemMutation();
  const [removeCartItem] = useRemoveCartItemMutation();
  const [clearCart] = useClearCartMutation();

  const items = useMemo(() => {
    const rows = Array.isArray(cart?.items) ? cart.items : [];
    return rows.map((it) => {
      const delivery = supplierToDelivery(it.supplierType);
      // Backend yo'riqnomasi: `productName === null` yoki `productId === null`
      // bo'lsa item "osiroten" (SKU katalogdan o'chirilgan yoki hech qachon
      // mavjud bo'lmagan). UI'da "товар недоступен" ko'rsatish kerak.
      const isOrphaned = !it.productName || !it.productId;
      return {
        id: it.id,
        skuId: it.skuId,
        productId: it.productId,
        variantId: it.variantId,
        name: String(it.productName || ""),
        variantLabel: String(it.variantLabel || ""),
        size: String(it.variantLabel || ""),
        article: it.skuId ? String(it.skuId).slice(0, 8).toUpperCase() : "",
        // Backend `imageUrl` absolute CDN URL (image_backend/MinIO) yoki
        // null. Null bo'lsa placeholder ko'rsatamiz (DRAFT/ENRICHING SKU
        // yoki o'chirilgan).
        image: toUiImage(it.imageUrl),
        priceRub: Number(it.priceRub) || 0,
        lineTotalRub: Number(it.lineTotalRub) || 0,
        quantity: Number(it.quantity) || 1,
        supplierType: it.supplierType,
        deliveryText: delivery,
        shippingText: delivery ? `Доставка ${delivery} до РФ 0₽` : "",
        addedAt: it.addedAt,
        isFavorite: false,
        isOrphaned,
      };
    });
  }, [cart]);

  const removeItem = useCallback(
    async (idOrSkuId) => {
      if (idOrSkuId == null) return;
      // Prefer skuId (backend indexes by sku_id); caller may pass either.
      const match = items.find((x) => x.id === idOrSkuId || x.skuId === idOrSkuId);
      const skuId = match?.skuId || idOrSkuId;
      await removeCartItem(skuId).unwrap().catch(() => null);
    },
    [items, removeCartItem],
  );

  const setQuantity = useCallback(
    async (idOrSkuId, quantity) => {
      if (idOrSkuId == null) return;
      const nextQty = Math.max(1, Math.min(99, Math.floor(Number(quantity) || 1)));
      const match = items.find((x) => x.id === idOrSkuId || x.skuId === idOrSkuId);
      const skuId = match?.skuId || idOrSkuId;
      await updateCartItem({ skuId, quantity: nextQty })
        .unwrap()
        .catch(() => null);
    },
    [items, updateCartItem],
  );

  const removeMany = useCallback(
    async (ids) => {
      if (!ids || ids.size === 0) return;
      await Promise.all(
        Array.from(ids).map((id) => {
          const match = items.find((x) => x.id === id || x.skuId === id);
          const skuId = match?.skuId || id;
          return removeCartItem(skuId).unwrap().catch(() => null);
        }),
      );
    },
    [items, removeCartItem],
  );

  const clear = useCallback(async () => {
    await clearCart().unwrap().catch(() => null);
  }, [clearCart]);

  const totalQuantity = useMemo(() => {
    const n = Number(cart?.total_items);
    if (Number.isFinite(n)) return n;
    return items.reduce((s, x) => s + (Number(x.quantity) || 0), 0);
  }, [cart, items]);

  const subtotalRub = useMemo(() => {
    const n = Number(cart?.total_amount);
    if (Number.isFinite(n)) return n;
    return items.reduce(
      (s, x) => s + (Number(x.lineTotalRub) || Number(x.priceRub) * x.quantity || 0),
      0,
    );
  }, [cart, items]);

  return {
    ready: !isLoading,
    isLoading: Boolean(isLoading),
    isFetching: Boolean(isFetching),
    isError: Boolean(isError),
    items,
    removeItem,
    setQuantity,
    removeMany,
    clear,
    totalQuantity,
    subtotalRub,
    cartId: cart?.id ?? null,
  };
}
