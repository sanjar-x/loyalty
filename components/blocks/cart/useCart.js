"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  useClearCartMutation,
  useGetMyCartQuery,
  useGetProductsByIdsQuery,
  useRemoveCartItemMutation,
  useUpdateCartItemMutation,
} from "@/lib/store/api";
import {
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "@/lib/format/backendAssets";

/**
 * @typedef {Object} CartItem
 * @property {number} id
 * @property {string} name
 * @property {string} shippingText
 * @property {string} image
 * @property {string=} size
 * @property {string=} article
 * @property {number} priceRub
 * @property {number} quantity
 * @property {string} deliveryText
 * @property {boolean} isFavorite
 */

const CART_UPDATED_EVENT = "loyaltymarket_cart_updated";
const CART_META_KEY = "loyaltymarket_cart_meta_v1";
const CART_META_UPDATED_EVENT = "loyaltymarket_cart_meta_updated";

function safeParseJsonObject(value) {
  if (typeof value !== "string" || !value) return null;
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed
      : null;
  } catch {
    return null;
  }
}

function readCartMeta() {
  try {
    const raw = localStorage.getItem(CART_META_KEY);
    const obj = safeParseJsonObject(raw);
    return obj || {};
  } catch {
    return {};
  }
}

function uniqNumbers(arr) {
  const out = [];
  const seen = new Set();
  for (const v of arr) {
    const n = Number(v);
    if (!Number.isFinite(n) || n <= 0) continue;
    if (seen.has(n)) continue;
    seen.add(n);
    out.push(n);
  }
  return out;
}

function getProductPhotoCandidates(product) {
  const candidates = [];

  const rawDirect =
    (typeof product?.image === "string" ? product.image : "") ||
    (typeof product?.image_url === "string" ? product.image_url : "") ||
    (typeof product?.photo === "string" ? product.photo : "") ||
    (typeof product?.photo_url === "string" ? product.photo_url : "");
  if (rawDirect && rawDirect.trim()) candidates.push(rawDirect.trim());

  const photos = Array.isArray(product?.photos) ? product.photos : [];
  const first = photos?.[0];
  const filename =
    typeof first === "string"
      ? first
      : first && typeof first === "object"
        ? (first.filename ?? first.file ?? first.path ?? first.url)
        : null;

  const raw = typeof filename === "string" ? filename.trim() : "";
  if (raw) {
    candidates.push(
      buildProductPhotoUrl(raw),
      buildBackendAssetUrl(raw, ["media"]),
      buildBackendAssetUrl(raw, ["static"]),
      buildBackendAssetUrl(raw, ["uploads"]),
      buildBackendAssetUrl(raw),
    );
  }

  return candidates.filter(Boolean);
}

export function useCart() {
  const { data: cart, isLoading, isFetching, isError } = useGetMyCartQuery();

  const productIds = useMemo(() => {
    const rows = Array.isArray(cart?.items) ? cart.items : [];
    const ids = rows.map((it) => it?.product?.id).filter((x) => x != null);
    return uniqNumbers(ids).sort((a, b) => a - b);
  }, [cart]);

  const { data: productsDetails } = useGetProductsByIdsQuery(productIds, {
    skip: productIds.length === 0,
  });

  const productsById = useMemo(() => {
    const map = new Map();
    const rows = Array.isArray(productsDetails) ? productsDetails : [];
    for (const p of rows) {
      const id = p?.id;
      if (id == null) continue;
      map.set(Number(id), p);
    }
    return map;
  }, [productsDetails]);

  const [updateCartItem] = useUpdateCartItemMutation();
  const [removeCartItem] = useRemoveCartItemMutation();
  const [clearCart] = useClearCartMutation();

  const [cartMeta, setCartMeta] = useState(() => readCartMeta());
  useEffect(() => {
    const onMeta = () => setCartMeta(readCartMeta());
    window.addEventListener(CART_META_UPDATED_EVENT, onMeta);
    return () => window.removeEventListener(CART_META_UPDATED_EVENT, onMeta);
  }, []);

  const ready = !isLoading;

  const items = useMemo(() => {
    const rows = Array.isArray(cart?.items) ? cart.items : [];
    return rows
      .map((it) => {
        const id = it?.id;
        const product = it?.product;
        const productId = product?.id;
        if (id == null) return null;

        const detailed =
          productId != null ? productsById.get(Number(productId)) : null;
        const productForUi = detailed ?? product;

        const deliveryRaw =
          typeof productForUi?.delivery === "string"
            ? productForUi.delivery
            : "";
        const delivery = deliveryRaw.trim();

        const deliveryDateRaw =
          typeof productForUi?.deliveryDate === "string"
            ? productForUi.deliveryDate
            : typeof productForUi?.delivery_date === "string"
              ? productForUi.delivery_date
              : "";
        const deliveryDate = deliveryDateRaw.trim();

        const deliverySubRaw =
          typeof productForUi?.deliverySub === "string"
            ? productForUi.deliverySub
            : typeof productForUi?.delivery_sub === "string"
              ? productForUi.delivery_sub
              : "";
        const deliverySub = deliverySubRaw.trim();

        const shippingText = delivery ? `Доставка из ${delivery} до РФ 0₽` : "";

        const deliveryText = (() => {
          if (deliveryDate && deliverySub)
            return `${deliveryDate}, ${deliverySub}`;
          if (deliveryDate && delivery)
            return `${deliveryDate}, из ${delivery}`;
          if (deliveryDate) return deliveryDate;
          if (delivery) return `из ${delivery}`;
          return "";
        })();

        const metaKey = productId != null ? String(Number(productId)) : "";
        const meta = metaKey ? cartMeta?.[metaKey] : null;

        const candidates = getProductPhotoCandidates(productForUi);
        const metaImage =
          typeof meta?.image === "string" ? meta.image.trim() : "";
        const image = candidates[0] ?? metaImage ?? "";

        const priceRub = Number(productForUi?.price);
        const lineTotalRub = Number(it?.line_total);
        const quantity = Number(it?.quantity);

        const metaSize = typeof meta?.size === "string" ? meta.size : undefined;
        const metaShipping =
          typeof meta?.shippingText === "string" ? meta.shippingText : "";
        const metaDelivery =
          typeof meta?.deliveryText === "string" ? meta.deliveryText : "";
        const metaArticle =
          typeof meta?.article === "string" ? meta.article : "";

        return {
          id,
          productId,
          name: String(productForUi?.name ?? ""),
          shippingText: shippingText || metaShipping,
          image,
          size: metaSize,
          article: String(
            productForUi?.article ??
              productForUi?.sku ??
              productForUi?.vendor_code ??
              metaArticle ??
              (productId != null ? String(productId) : ""),
          ),
          priceRub: Number.isFinite(priceRub) ? priceRub : 0,
          quantity: Number.isFinite(quantity) && quantity > 0 ? quantity : 1,
          lineTotalRub: Number.isFinite(lineTotalRub)
            ? lineTotalRub
            : Number.isFinite(priceRub) && Number.isFinite(quantity)
              ? priceRub * quantity
              : 0,
          deliveryText: deliveryText || metaDelivery,
          isFavorite: false,
        };
      })
      .filter(Boolean);
  }, [cart, cartMeta, productsById]);

  useEffect(() => {
    if (!ready) return;
    try {
      window.dispatchEvent(new Event(CART_UPDATED_EVENT));
    } catch {
      // ignore
    }
  }, [items, ready]);

  const toggleFavorite = useCallback(() => {
    // Favorites are handled via useItemFavorites("product") on pages.
  }, []);

  const removeItem = useCallback(
    async (id) => {
      if (id == null) return;
      await removeCartItem(id);
    },
    [removeCartItem],
  );

  const setQuantity = useCallback(
    async (id, quantity) => {
      if (id == null) return;
      const nextQty = Math.max(1, Number(quantity || 1));
      await updateCartItem({ itemId: id, quantity: nextQty });
    },
    [updateCartItem],
  );

  const removeMany = useCallback(
    async (ids) => {
      if (!ids || ids.size === 0) return;
      await Promise.all(Array.from(ids).map((id) => removeCartItem(id)));
    },
    [removeCartItem],
  );

  const clear = useCallback(async () => {
    await clearCart();
  }, [clearCart]);

  const totalQuantity = useMemo(() => {
    const n = Number(cart?.total_items);
    if (Number.isFinite(n)) return n;
    return items.reduce((sum, x) => sum + (Number(x?.quantity) || 0), 0);
  }, [cart, items]);

  const subtotalRub = useMemo(() => {
    const n = Number(cart?.total_amount);
    if (Number.isFinite(n)) return n;
    return items.reduce(
      (sum, x) =>
        sum +
        (Number(x?.lineTotalRub) ||
          Number(x?.priceRub) * Number(x?.quantity) ||
          0),
      0,
    );
  }, [cart, items]);

  return {
    ready,
    isLoading: Boolean(isLoading),
    isFetching: Boolean(isFetching),
    isError: Boolean(isError),
    items,
    toggleFavorite,
    removeItem,
    setQuantity,
    removeMany,
    clear,
    totalQuantity,
    subtotalRub,
  };
}
