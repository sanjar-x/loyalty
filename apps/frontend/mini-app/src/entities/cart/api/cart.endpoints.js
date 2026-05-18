/**
 * RTKQ endpoint enhancement configs — Cart.
 *
 * `onQueryStarted` optimistic patches use `baseApi.util.updateQueryData`:
 * `baseApi` === `enhancedApi` (single instance, `reducerPath:"api"`) — it used
 * to be `enhancedApi.util`, but that one is created in `instance.js`
 * (circular import). The endpoint name string is unchanged, the behavior is identical.
 */
import { baseApi } from '@/shared/api/base-api/baseApi';
import {
  moneyToRub,
  normalizeCartResponse,
  recalcCartTotals,
} from '@/entities/cart/lib/cartHelpers';

export const cartEndpoints = {
  /* ─── Cart ─── */
  getCartApiV1CartGet: {
    transformResponse: (response) => normalizeCartResponse(response),
    providesTags: ['Cart'],
  },
  getCartSummaryApiV1CartSummaryGet: {
    transformResponse: (response) => ({
      itemCount: Number(response?.itemCount) || 0,
      totalRub: moneyToRub(response?.total),
      currency: response?.total?.currency ?? 'RUB',
    }),
    providesTags: ['Cart'],
  },
  clearCartApiV1CartDelete: {
    invalidatesTags: ['Cart'],
    async onQueryStarted(_arg, { dispatch, queryFulfilled }) {
      const patch = dispatch(
        baseApi.util.updateQueryData(
          'getCartApiV1CartGet',
          { 'x-anonymous-token': undefined },
          (draft) => {
            if (!draft || typeof draft !== 'object') return;
            draft.items = [];
            draft.groups = [];
            draft.total_items = 0;
            draft.total_amount = 0;
          }
        )
      );
      try {
        await queryFulfilled;
      } catch {
        patch.undo();
      }
    },
  },
  addItemApiV1CartItemsPost: {
    invalidatesTags: ['Cart'],
    async onQueryStarted(arg, { dispatch, queryFulfilled }) {
      const payload = arg?.addItemRequest;
      const skuId = payload?.skuId;
      const qty = Math.max(1, Math.floor(Number(payload?.quantity || 1)));
      if (!skuId) return;

      const patch = dispatch(
        baseApi.util.updateQueryData(
          'getCartApiV1CartGet',
          { 'x-anonymous-token': undefined },
          (draft) => {
            if (!draft || typeof draft !== 'object') return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const idx = list.findIndex((x) => String(x?.skuId) === String(skuId));
            if (idx >= 0) {
              const prev = Number(list[idx]?.quantity) || 0;
              list[idx].quantity = prev + qty;
              const price = Number(list[idx]?.priceRub) || 0;
              list[idx].lineTotalRub = price * list[idx].quantity;
            } else {
              list.push({
                id: null,
                skuId,
                productId: arg?.productId ?? null,
                variantId: arg?.variantId ?? null,
                productName: arg?.productName ?? '',
                variantLabel: arg?.variantLabel ?? '',
                imageUrl: arg?.imageUrl ?? '',
                quantity: qty,
                priceRub: Number(arg?.priceRub) || 0,
                lineTotalRub: (Number(arg?.priceRub) || 0) * qty,
                supplierType: arg?.supplierType ?? '',
                addedAt: new Date().toISOString(),
              });
            }
            draft.items = list;
            recalcCartTotals(draft);
          }
        )
      );

      try {
        await queryFulfilled;
      } catch {
        patch.undo();
      }
    },
  },
  updateQuantityApiV1CartItemsSkuIdPatch: {
    invalidatesTags: ['Cart'],
    async onQueryStarted(arg, { dispatch, queryFulfilled }) {
      const skuId = arg?.skuId;
      const nextQty = Number(arg?.updateQuantityRequest?.quantity);
      const patch = dispatch(
        baseApi.util.updateQueryData(
          'getCartApiV1CartGet',
          { 'x-anonymous-token': undefined },
          (draft) => {
            if (!draft || typeof draft !== 'object') return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const idx = list.findIndex((x) => String(x?.skuId) === String(skuId));
            if (idx < 0 || !Number.isFinite(nextQty) || nextQty < 0) return;

            if (nextQty === 0) {
              list.splice(idx, 1);
            } else {
              list[idx].quantity = nextQty;
              const price = Number(list[idx]?.priceRub) || 0;
              list[idx].lineTotalRub = price * nextQty;
            }
            draft.items = list;
            recalcCartTotals(draft);
          }
        )
      );

      try {
        await queryFulfilled;
      } catch {
        patch.undo();
      }
    },
  },
  removeItemApiV1CartItemsSkuIdDelete: {
    invalidatesTags: ['Cart'],
    async onQueryStarted(arg, { dispatch, queryFulfilled }) {
      const skuId = arg?.skuId;
      const patch = dispatch(
        baseApi.util.updateQueryData(
          'getCartApiV1CartGet',
          { 'x-anonymous-token': undefined },
          (draft) => {
            if (!draft || typeof draft !== 'object') return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            draft.items = list.filter((x) => String(x?.skuId) !== String(skuId));
            recalcCartTotals(draft);
          }
        )
      );
      try {
        await queryFulfilled;
      } catch {
        patch.undo();
      }
    },
  },
  confirmCheckoutApiV1CartCheckoutConfirmPost: {
    invalidatesTags: ['Cart', 'Orders'],
  },
  cancelCheckoutApiV1CartCheckoutCancelPost: {
    invalidatesTags: ['Cart'],
  },
  mergeCartsApiV1CartMergePost: {
    invalidatesTags: ['Cart'],
  },
};
