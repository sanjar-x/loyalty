/**
 * RTK Query — "clean" hook re-export qatlami.
 *
 * Codegen'ning "uzun" hook nomlarini call-site'larga mos qisqa nomlar bilan
 * re-export qiladi. Audit #8: ilgari yagona `notImplemented*` stub'lar edi —
 * ikki kategoriyaga ajratildi:
 *
 *  • `adminOnlyMutation` — customer app'da **hech qachon** ishlatilmaydigan
 *    admin endpoint'lar (catalog/brand CRUD, order status edit). Chaqirilsa
 *    rejection beradi (programming error sifatida).
 *  • `pendingFeatureQuery` — backend hali ship qilmagan **customer feature**
 *    (referrals, loyalty points, va h.k. — Spec §11). Empty data qaytaradi,
 *    UI graceful render qiladi. Backend ship qilganda: `FEATURES.<FLAG> ?
 *    realRtkHook : stub` pattern (`@/lib/featureFlags`).
 */
import { enhancedApi, customApi } from './instance';
import { setPendingIdempotencyKey, clearPendingIdempotencyKey } from '@/lib/store/baseApi';

const pendingFeatureQuery = () => ({
  data: undefined,
  isLoading: false,
  isFetching: false,
  isError: false,
  error: undefined,
  refetch: () => Promise.resolve(),
});
const adminOnlyMutation = () => [
  () => Promise.reject(new Error('Admin operation — not exposed in customer app')),
  { isLoading: false, isError: false, error: undefined, reset: () => {} },
];

/* User */
export const useGetMeQuery = enhancedApi.useGetMyProfileApiV1ProfileMeGetQuery;

/* Products / catalog */
export const useGetProductsQuery = (params, opts) =>
  enhancedApi.useListStorefrontProductsApiV1StorefrontProductsGetQuery(
    {
      categoryId: params?.category_id,
      brandId: params?.brand_id,
      priceMin: params?.price_min,
      priceMax: params?.price_max,
      inStock: params?.in_stock,
      sort: params?.sort,
      limit: params?.limit,
      cursor: params?.cursor,
      includeTotal: params?.include_total,
      includeFacets: params?.include_facets,
      lang: params?.lang,
    },
    opts
  );
export const useLazyGetProductsQuery =
  enhancedApi.useLazyListStorefrontProductsApiV1StorefrontProductsGetQuery;

export const useGetProductByIdQuery = (slugOrId, opts) =>
  enhancedApi.useGetStorefrontProductApiV1StorefrontProductsSlugGetQuery(
    { slug: String(slugOrId) },
    opts
  );

export const useGetSimilarProductsQuery = ({ slug, limit = 12 } = {}, opts) =>
  enhancedApi.useGetSimilarProductsApiV1StorefrontProductsSlugSimilarGetQuery(
    { slug, limit },
    opts
  );

export const useGetAlsoViewedProductsQuery = ({ slug, limit = 12 } = {}, opts) =>
  enhancedApi.useGetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetQuery(
    { slug, limit },
    opts
  );

export const useGetProductMediaQuery = ({ productId, limit = 50 } = {}, opts) =>
  enhancedApi.useListProductMediaApiV1AdminCatalogProductsProductIdMediaGetQuery(
    { productId, limit },
    opts
  );

export const useGetProductsByIdsQuery = customApi.useGetProductsByIdsQuery;

export const useGetLatestProductsQuery = (params, opts) => {
  const limit = typeof params === 'object' && params != null ? params?.limit : params;
  const n = limit == null ? null : Number(limit);
  const safe = typeof n === 'number' && Number.isFinite(n) && n > 0 ? Math.floor(n) : undefined;
  return enhancedApi.useListStorefrontProductsApiV1StorefrontProductsGetQuery(
    {
      categoryId: params && typeof params === 'object' ? params?.category_id : undefined,
      sort: 'newest',
      limit: safe,
    },
    opts
  );
};

export const useGetLatestPurchasedProductsQuery = (params, opts) => {
  const result = useGetLatestProductsQuery(params, opts);
  return {
    ...result,
    data: Array.isArray(result?.data?.items) ? result.data.items : [],
  };
};

export const useGetForYouFeedQuery = (params, opts) =>
  enhancedApi.useGetForYouFeedApiV1StorefrontForYouGetQuery(
    {
      limit: params?.limit,
      cursor: params?.cursor,
      lang: params?.lang,
    },
    opts
  );
export const useLazyGetForYouFeedQuery =
  enhancedApi.useLazyGetForYouFeedApiV1StorefrontForYouGetQuery;

export const useGetTrendingProductsQuery = (params, opts) =>
  enhancedApi.useListTrendingProductsApiV1StorefrontTrendingGetQuery(
    {
      limit: params?.limit,
      window: params?.window,
      categoryId: params?.category_id,
      lang: params?.lang,
    },
    opts
  );
export const useLazyGetTrendingProductsQuery =
  enhancedApi.useLazyListTrendingProductsApiV1StorefrontTrendingGetQuery;

/* Categories / Brands */
export const useGetCategoryTreeQuery = (arg, opts) => {
  const maxDepth = Number(arg?.maxDepth);
  const safe = Number.isInteger(maxDepth) && maxDepth >= 1 && maxDepth <= 10 ? maxDepth : undefined;
  return enhancedApi.useStorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetQuery(
    { maxDepth: safe },
    opts
  );
};

export const useGetCategoriesQuery = (arg, opts) =>
  enhancedApi.useStorefrontListCategoriesApiV1StorefrontCategoriesGetQuery(
    { limit: 100, ...(arg || {}) },
    opts
  );

export const useGetBrandsQuery = (arg, opts) =>
  enhancedApi.useStorefrontListBrandsApiV1StorefrontBrandsGetQuery(
    { limit: 200, ...(arg || {}) },
    opts
  );

export const useSearchBrandsQuery = customApi.useSearchBrandsQuery;

export const useGetBrandByIdQuery = (brandId, opts) =>
  enhancedApi.useStorefrontGetBrandApiV1StorefrontBrandsBrandIdGetQuery({ brandId }, opts);

/* Admin operations — customer app'ida ishlatilmaydigan stub'lar */
export const useCreateCategoryMutation = adminOnlyMutation;
export const useDeleteCategoryMutation = adminOnlyMutation;
export const useCreateBrandMutation = adminOnlyMutation;
export const useDeleteBrandMutation = adminOnlyMutation;
export const useUploadBrandLogoMutation = adminOnlyMutation;
export const useDeleteBrandLogoMutation = adminOnlyMutation;
export const useGetCategoriesWithTypesQuery = () => ({
  ...pendingFeatureQuery(),
  data: [],
});
export const useGetTypesByCategoryQuery = () => ({
  ...pendingFeatureQuery(),
  data: [],
});

/* Favorites — to'liq v1 contract (UUID + target_type/target_id) ─────────────
 *
 * Domain modeli:
 *  • FavoriteList — userning kollektsiyasi (default + custom).
 *  • FavoriteItem — listga biriktirilgan target (product yoki brand).
 *  • Bulk check — render qilinayotgan target_id ro'yxatini bir POST'da
 *    favorited holatini tekshirish (PLP/PDP/cards uchun).
 *
 * Higher-level wrapper'lar `lib/hooks/useItemFavorites.js` va
 * `lib/hooks/useFavoriteLists.js` da yashaydi — sahifalar to'g'ridan-to'g'ri
 * shu xom hook'larni emas, wrapper'larni ishlatadi (default list resolver,
 * optimistic toggle, auth gate hammasi shu yerda).
 */
export const useGetFavoriteListsQuery = enhancedApi.useListFavoriteListsApiV1FavoritesListsGetQuery;
export const useListFavoriteItemsQuery =
  enhancedApi.useListFavoriteItemsApiV1FavoritesListsListIdItemsGetQuery;
export const useCreateFavoriteListMutation =
  enhancedApi.useCreateFavoriteListApiV1FavoritesListsPostMutation;
export const useRenameFavoriteListMutation =
  enhancedApi.useRenameFavoriteListApiV1FavoritesListsListIdPatchMutation;
export const useDeleteFavoriteListMutation =
  enhancedApi.useDeleteFavoriteListApiV1FavoritesListsListIdDeleteMutation;
export const useAddFavoriteItemMutation =
  enhancedApi.useAddFavoriteItemApiV1FavoritesItemsPostMutation;
export const useRemoveFavoriteItemMutation =
  enhancedApi.useRemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteMutation;
export const useMoveFavoriteItemMutation =
  enhancedApi.useMoveFavoriteItemApiV1FavoritesItemsMovePostMutation;
export const useCheckFavoritedItemsQuery = customApi.useCheckFavoritedItemsQuery;

/* Referrals — backend'da hali yo'q (Spec §11), bo'sh fallback */
export const useGetMyReferralLinkQuery = () => ({
  ...pendingFeatureQuery(),
  data: null,
});
export const useGetMyInvitedUsersQuery = () => ({
  ...pendingFeatureQuery(),
  data: [],
});
export const useGetMyActiveDiscountQuery = () => ({
  ...pendingFeatureQuery(),
  data: null,
});
export const useGetMyReferralStatsQuery = () => ({
  ...pendingFeatureQuery(),
  data: { invitedCount: 0, totalDiscountRub: 0 },
});

/* Cart */
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
      // optimistic patch metadata
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

/* Checkout — yangi schema {pickupPointId, pickupCarrier, recipientId} */
const INITIATE_CHECKOUT_URL = '/api/v1/cart/checkout';
const CREATE_ORDER_URL = '/api/v1/orders';

export { clearPendingIdempotencyKey, INITIATE_CHECKOUT_URL, CREATE_ORDER_URL };

export const useInitiateCheckoutMutation = () => {
  const [trigger, state] = enhancedApi.useInitiateCheckoutApiV1CartCheckoutPostMutation();
  const wrapped = (body) => {
    // CHK-006: Idempotency-Key codegen `query(arg)`'da body'ga ham,
    // header'ga ham mapping topmaydi — yon-kanal orqali baseQuery
    // registry'siga yozamiz; o'zining baseQuery'si URL bo'yicha o'qiydi.
    if (body?.__idempotencyKey) {
      setPendingIdempotencyKey(INITIATE_CHECKOUT_URL, body.__idempotencyKey);
    }
    return trigger({
      initiateCheckoutRequest: {
        pickupPointId: body?.pickupPointId,
        pickupCarrier: body?.pickupCarrier,
        recipientId: body?.recipientId,
      },
    });
  };
  return [wrapped, state];
};

export const useConfirmCheckoutMutation = () => {
  const [trigger, state] = enhancedApi.useConfirmCheckoutApiV1CartCheckoutConfirmPostMutation();
  const wrapped = (body) => trigger({ confirmCheckoutRequest: { attemptId: body?.attemptId } });
  return [wrapped, state];
};

export const useCancelCheckoutMutation =
  enhancedApi.useCancelCheckoutApiV1CartCheckoutCancelPostMutation;

export const useGetAnonymousCartTokenMutation =
  enhancedApi.useCreateAnonymousTokenApiV1CartAnonymousTokenPostMutation;

export const useMergeCartMutation = () => {
  const [trigger, state] = enhancedApi.useMergeCartsApiV1CartMergePostMutation();
  const wrapped = ({ anonymousToken }) => trigger({ mergeCartRequest: { anonymousToken } });
  return [wrapped, state];
};

/* Pickup-points (custom POST-as-query) */
export const useListPickupPointsQuery = customApi.useStorefrontPickupPointsQuery;

/* Rate quote (custom — admin-only path) */
export const useGetRateQuoteMutation = customApi.useGetRateQuoteMutation;

/* Orders */
export const useListOrdersQuery = (arg, opts) =>
  enhancedApi.useListMyOrdersApiV1OrdersGetQuery({ limit: arg?.limit, cursor: arg?.cursor }, opts);

export const useGetOrderByIdQuery = (orderId, opts) =>
  enhancedApi.useGetOrderApiV1OrdersOrderIdGetQuery({ orderId }, opts);

export const useGetOrderTrackingQuery = (orderId, opts) =>
  enhancedApi.useGetOrderTrackingApiV1OrdersOrderIdTrackingGetQuery({ orderId }, opts);

export const useCreateOrderMutation = () => {
  const [trigger, state] = enhancedApi.useCreateOrderApiV1OrdersPostMutation();
  // CHK-024: deliveryQuoteId — `RateQuoteResponse.quoteId`. Backend
  // quote'dan deliveryAmount'ni totalAmount va payment authorize'ga
  // qo'shadi. CHK-006: Idempotency-Key codegen mapping topmaydi —
  // yon-kanal orqali baseQuery registry'siga yozamiz (xuddi
  // useInitiateCheckoutMutation'dagi pattern).
  const wrapped = (body) => {
    if (body?.__idempotencyKey) {
      setPendingIdempotencyKey(CREATE_ORDER_URL, body.__idempotencyKey);
    }
    return trigger({
      createOrderRequest: {
        cartId: body?.cartId,
        snapshotId: body?.snapshotId,
        idempotencyKey: body?.idempotencyKey,
        paymentProvider: body?.paymentProvider || 'fake',
        deliveryQuoteId: body?.deliveryQuoteId ?? null,
      },
    });
  };
  return [wrapped, state];
};

export const useCancelOrderMutation = () => {
  const [trigger, state] = enhancedApi.useCancelOrderApiV1OrdersOrderIdCancelPostMutation();
  const wrapped = ({ orderId, reason }) =>
    trigger({
      orderId,
      cancelOrderRequest: reason ? { reason } : {},
    });
  return [wrapped, state];
};

export const useUpdateOrderStatusMutation = adminOnlyMutation;
export const useGetOrderStatusQuery = () => ({
  ...pendingFeatureQuery(),
  data: null,
});

/* Recipients */
export const useListMyRecipientsQuery = enhancedApi.useListMyRecipientsApiV1RecipientsGetQuery;
export const useGetRecipientQuery = (recipientId, opts) =>
  enhancedApi.useGetRecipientApiV1RecipientsRecipientIdGetQuery({ recipientId }, opts);
export const useCreateRecipientMutation = () => {
  const [trigger, state] = enhancedApi.useCreateRecipientApiV1RecipientsPostMutation();
  const wrapped = (body) => trigger({ createRecipientRequest: body });
  return [wrapped, state];
};
export const useUpdateRecipientMutation = () => {
  const [trigger, state] = enhancedApi.useUpdateRecipientApiV1RecipientsRecipientIdPatchMutation();
  const wrapped = ({ recipientId, ...body }) =>
    trigger({ recipientId, updateRecipientRequest: body });
  return [wrapped, state];
};
export const useArchiveRecipientMutation =
  enhancedApi.useArchiveRecipientApiV1RecipientsRecipientIdDeleteMutation;

/* Search */
export const useGetSearchSuggestionsQuery = (rawQuery, opts) => {
  const q = typeof rawQuery === 'string' ? rawQuery.trim() : '';
  return enhancedApi.useSearchSuggestApiV1StorefrontSearchSuggestGetQuery({ q, limit: 10 }, opts);
};

/* Search history (custom — localStorage) */
export const useGetSearchHistoryQuery = customApi.useGetSearchHistoryQuery;
export const useCreateSearchHistoryMutation = customApi.useCreateSearchHistoryMutation;
export const useRemoveSearchHistoryItemMutation = customApi.useRemoveSearchHistoryItemMutation;
export const useClearSearchHistoryMutation = customApi.useClearSearchHistoryMutation;
