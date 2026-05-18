/** Sprint 3d: Cart RTKQ hooks (with wrapper for optimistic patch metadata). */
import { enhancedApi } from '@/app/providers/store/instance';

export const useGetMyCartQuery = (_arg, opts) =>
  enhancedApi.useGetCartApiV1CartGetQuery({ 'x-anonymous-token': undefined }, opts);

export const useGetCartSummaryQuery = (_arg, opts) =>
  enhancedApi.useGetCartSummaryApiV1CartSummaryGetQuery({ 'x-anonymous-token': undefined }, opts);

export const useClearCartMutation = () => {
  const [trigger, state] = enhancedApi.useClearCartApiV1CartDeleteMutation();
  return [() => trigger({ 'x-anonymous-token': undefined }), state];
};

export const useAddCartItemMutation = () => {
  const [trigger, state] = enhancedApi.useAddItemApiV1CartItemsPostMutation();
  const wrapped = (payload) =>
    trigger({
      'x-anonymous-token': undefined,
      addItemRequest: {
        skuId: payload?.skuId,
        quantity: Math.max(1, Math.floor(Number(payload?.quantity || 1))),
      },
      productId: payload?.productId,
      variantId: payload?.variantId,
      productName: payload?.productName,
      variantLabel: payload?.variantLabel,
      imageUrl: payload?.imageUrl,
      priceRub: payload?.priceRub,
      supplierType: payload?.supplierType,
    });
  return [wrapped, state];
};

export const useUpdateCartItemMutation = () => {
  const [trigger, state] = enhancedApi.useUpdateQuantityApiV1CartItemsSkuIdPatchMutation();
  const wrapped = ({ skuId, quantity }) =>
    trigger({
      skuId: String(skuId),
      'x-anonymous-token': undefined,
      updateQuantityRequest: {
        quantity: Math.max(1, Math.floor(Number(quantity || 1))),
      },
    });
  return [wrapped, state];
};

export const useRemoveCartItemMutation = () => {
  const [trigger, state] = enhancedApi.useRemoveItemApiV1CartItemsSkuIdDeleteMutation();
  const wrapped = (skuId) => trigger({ skuId: String(skuId), 'x-anonymous-token': undefined });
  return [wrapped, state];
};
