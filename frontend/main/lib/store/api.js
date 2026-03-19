import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

function recalcCartTotals(cart) {
  if (!cart || typeof cart !== "object") return;
  const items = Array.isArray(cart.items) ? cart.items : [];
  let totalItems = 0;
  let totalAmount = 0;
  for (const it of items) {
    const qty = Number(it?.quantity);
    const q = Number.isFinite(qty) && qty > 0 ? qty : 0;
    totalItems += q;

    const lineTotal = Number(it?.line_total);
    if (Number.isFinite(lineTotal)) {
      totalAmount += lineTotal;
      continue;
    }

    const price = Number(it?.product?.price);
    if (Number.isFinite(price)) totalAmount += price * q;
  }

  cart.total_items = totalItems;
  cart.total_amount = totalAmount;
}

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include", // httpOnly cookie session
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

const baseQuery = async (args, api, extraOptions) => {
  const url = typeof args === "string" ? args : args?.url;

  // Local Next.js routes (not proxied to backend)
  if (typeof url === "string" && url.startsWith("/api/session/")) {
    return appBaseQuery(args, api, extraOptions);
  }

  // Default: backend calls through /api/backend proxy
  return backendBaseQuery(args, api, extraOptions);
};

export const api = createApi({
  reducerPath: "api",
  baseQuery,
  tagTypes: [
    "User",
    "Products",
    "Product",
    "Categories",
    "Types",
    "Brands",
    "Favorites",
    "Cart",
    "Orders",
    "Payments",
    "Shipments",
    "Referrals",
    "PVZ",
    "SearchHistory",
  ],
  endpoints: (builder) => ({
    initTelegramSession: builder.mutation({
      query: (payload) => ({
        url: "/api/session/telegram/init",
        method: "POST",
        headers: { "content-type": "application/json" },
        body:
          typeof payload === "string"
            ? { initData: payload }
            : payload && typeof payload === "object"
              ? payload
              : {},
      }),
      invalidatesTags: ["User"],
    }),

    // Session/User
    getMe: builder.query({
      query: () => "/api/v1/users",
      providesTags: ["User"],
    }),

    // Products
    getProducts: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.skip != null) sp.set("skip", String(params.skip));
        if (params?.limit != null) sp.set("limit", String(params.limit));
        if (params?.category_id != null)
          sp.set("category_id", String(params.category_id));

        const typeId = Array.isArray(params?.type_id)
          ? params.type_id[0]
          : params?.type_id;
        if (typeId != null) sp.set("type_id", String(typeId));

        const brandId = Array.isArray(params?.brand_id)
          ? params.brand_id[0]
          : params?.brand_id;
        if (brandId != null) sp.set("brand_id", String(brandId));

        if (params?.price_min != null)
          sp.set("price_min", String(params.price_min));
        if (params?.price_max != null)
          sp.set("price_max", String(params.price_max));
        const qs = sp.toString();
        return qs ? `/api/v1/products/?${qs}` : "/api/v1/products/";
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Products"];
        return [
          "Products",
          ...result
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    getProductById: builder.query({
      query: (productId) => `/api/v1/products/${productId}`,
      providesTags: (result, err, productId) => [
        { type: "Product", id: productId },
      ],
    }),

    getProductsByIds: builder.query({
      async queryFn(ids, _api, _extraOptions, baseQuery) {
        const raw = Array.isArray(ids) ? ids : [];
        const uniqueIds = Array.from(
          new Set(
            raw
              .map((x) => {
                const n = Number(x);
                return Number.isFinite(n) && n > 0 ? n : null;
              })
              .filter((x) => x != null),
          ),
        ).sort((a, b) => a - b);

        if (uniqueIds.length === 0) return { data: [] };

        // Reuse RTK Query per-product cache where possible.
        // This prevents refetching all products when the ids array changes.
        const state = _api.getState();

        const products = await Promise.all(
          uniqueIds.map(async (id) => {
            try {
              const cached = api.endpoints.getProductById.select(id)(state);
              if (cached?.data && typeof cached.data === "object") {
                return cached.data;
              }

              // subscribe:false -> don't keep extra subscriptions alive
              const result = await _api
                .dispatch(
                  api.endpoints.getProductById.initiate(id, {
                    subscribe: false,
                    forceRefetch: false,
                  }),
                )
                .unwrap();
              return result && typeof result === "object" ? result : null;
            } catch {
              // Fallback to direct call if initiate fails for any reason.
              const r = await baseQuery(`/api/v1/products/${id}`);
              const data = r && typeof r === "object" ? r.data : null;
              return data && typeof data === "object" ? data : null;
            }
          }),
        );

        return {
          data: products.filter((p) => p && typeof p === "object"),
        };
      },
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Products"];
        return [
          "Products",
          ...result
            .map((p) => (p && typeof p === "object" ? p.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Product", id })),
        ];
      },
    }),

    getLatestProducts: builder.query({
      query: (limit) => {
        const n = limit == null ? null : Number(limit);
        if (typeof n === "number" && Number.isFinite(n) && n > 0) {
          return `/api/v1/products/latest?limit=${encodeURIComponent(String(Math.floor(n)))}`;
        }
        return "/api/v1/products/latest";
      },
      providesTags: ["Products"],
    }),

    getLatestPurchasedProducts: builder.query({
      query: (limit) => {
        const n = limit == null ? null : Number(limit);
        if (typeof n === "number" && Number.isFinite(n) && n > 0) {
          return `/api/v1/products/latest-purchased?limit=${encodeURIComponent(String(Math.floor(n)))}`;
        }
        return "/api/v1/products/latest-purchased";
      },
      providesTags: ["Products"],
    }),

    // Categories
    getCategories: builder.query({
      query: () => "/api/v1/categories",
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Categories"];
        return [
          "Categories",
          ...result
            .map((c) => (c && typeof c === "object" ? c.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Categories", id })),
        ];
      },
    }),
    createCategory: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/categories",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Categories"],
    }),
    deleteCategory: builder.mutation({
      query: (categoryId) => ({
        url: `/api/v1/categories/${encodeURIComponent(String(categoryId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Categories"],
    }),

    // Types
    getCategoriesWithTypes: builder.query({
      query: () => "/api/v1/types",
      providesTags: ["Types"],
    }),
    getTypesByCategory: builder.query({
      query: (categoryId) =>
        `/api/v1/types/${encodeURIComponent(String(categoryId))}`,
      providesTags: ["Types"],
    }),
    createType: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/types",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Types"],
    }),
    updateType: builder.mutation({
      query: ({ typeId, ...payload }) => ({
        url: `/api/v1/types/${encodeURIComponent(String(typeId))}`,
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Types"],
    }),
    deleteType: builder.mutation({
      query: (typeId) => ({
        url: `/api/v1/types/${encodeURIComponent(String(typeId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Types"],
    }),

    // Brands
    getBrands: builder.query({
      query: () => "/api/v1/brands",
      providesTags: (result) => {
        if (!Array.isArray(result)) return ["Brands"];
        return [
          "Brands",
          ...result
            .map((b) => (b && typeof b === "object" ? b.id : null))
            .filter((id) => id != null)
            .map((id) => ({ type: "Brands", id })),
        ];
      },
    }),
    searchBrands: builder.query({
      query: ({ q, limit, offset } = {}) => {
        const sp = new URLSearchParams();
        if (q != null) sp.set("q", String(q));
        if (limit != null) sp.set("limit", String(limit));
        if (offset != null) sp.set("offset", String(offset));
        return `/api/v1/brands/search?${sp.toString()}`;
      },
      providesTags: ["Brands"],
    }),
    getBrandById: builder.query({
      query: (brandId) =>
        `/api/v1/brands/${encodeURIComponent(String(brandId))}`,
      providesTags: (_result, _err, brandId) => [
        { type: "Brands", id: brandId },
      ],
    }),
    createBrand: builder.mutation({
      query: (formData) => ({
        url: "/api/v1/brands",
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["Brands"],
    }),
    deleteBrand: builder.mutation({
      query: (brandId) => ({
        url: `/api/v1/brands/${encodeURIComponent(String(brandId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Brands"],
    }),
    uploadBrandLogo: builder.mutation({
      query: ({ brandId, formData }) => ({
        url: `/api/v1/brands/${encodeURIComponent(String(brandId))}/logo`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: (_result, _err, { brandId }) => [
        "Brands",
        { type: "Brands", id: brandId },
      ],
    }),
    deleteBrandLogo: builder.mutation({
      query: (brandId) => ({
        url: `/api/v1/brands/${encodeURIComponent(String(brandId))}/logo`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _err, brandId) => [
        "Brands",
        { type: "Brands", id: brandId },
      ],
    }),

    // Favorites
    getFavorites: builder.query({
      query: (params) => {
        const sp = new URLSearchParams();
        if (params?.item_type != null)
          sp.set("item_type", String(params.item_type));
        if (params?.brand_id != null)
          sp.set("brand_id", String(params.brand_id));
        const qs = sp.toString();
        return qs ? `/api/v1/favorites?${qs}` : "/api/v1/favorites";
      },
      providesTags: ["Favorites"],
    }),
    addFavorite: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/favorites",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Favorites"],
    }),
    removeFavorite: builder.mutation({
      query: (favoriteId) => ({
        url: `/api/v1/favorites/${encodeURIComponent(String(favoriteId))}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Favorites"],
    }),

    // Referrals
    getMyReferralLink: builder.query({
      query: () => "/api/v1/referrals/link",
      providesTags: ["Referrals"],
    }),
    getMyInvitedUsers: builder.query({
      query: () => "/api/v1/referrals/invited",
      providesTags: ["Referrals"],
    }),
    getMyActiveDiscount: builder.query({
      query: () => "/api/v1/referrals/discount",
      providesTags: ["Referrals"],
    }),
    getMyReferralStats: builder.query({
      query: () => "/api/v1/referrals/stats",
      providesTags: ["Referrals"],
    }),

    // Cart
    getMyCart: builder.query({
      query: () => "/api/v1/cart",
      providesTags: ["Cart"],
    }),
    clearCart: builder.mutation({
      query: () => ({
        url: "/api/v1/cart",
        method: "DELETE",
      }),
      async onQueryStarted(_arg, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            draft.items = [];
            draft.total_items = 0;
            draft.total_amount = 0;
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    addCartItem: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/cart/items",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      async onQueryStarted(payload, { dispatch, queryFulfilled }) {
        const productId = payload?.product_id;
        const qtyRaw = payload?.quantity;
        const qty = Math.max(1, Math.floor(Number(qtyRaw || 1)));
        const tempId = -Math.floor(Math.random() * 1_000_000_000);

        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];

            const existingIdx = list.findIndex(
              (x) => String(x?.product?.id) === String(productId),
            );

            if (existingIdx >= 0) {
              const prevQty = Number(list[existingIdx]?.quantity);
              const nextQty = (Number.isFinite(prevQty) ? prevQty : 0) + qty;
              list[existingIdx].quantity = nextQty;
              const price = Number(list[existingIdx]?.product?.price);
              if (Number.isFinite(price))
                list[existingIdx].line_total = price * nextQty;
            } else {
              list.push({
                id: tempId,
                product: { id: productId },
                quantity: qty,
                line_total: 0,
              });
            }

            draft.items = list;
            recalcCartTotals(draft);
          }),
        );

        try {
          const res = await queryFulfilled;
          const data = res?.data;

          // If backend returns a cart object, prefer it.
          if (data && typeof data === "object" && Array.isArray(data.items)) {
            dispatch(
              api.util.updateQueryData("getMyCart", undefined, (draft) => {
                if (!draft || typeof draft !== "object") return;
                Object.assign(draft, data);
              }),
            );
            return;
          }

          // If backend returns a cart item, replace temporary item.
          if (data && typeof data === "object" && data.id != null) {
            dispatch(
              api.util.updateQueryData("getMyCart", undefined, (draft) => {
                if (!draft || typeof draft !== "object") return;
                const list = Array.isArray(draft.items) ? draft.items : [];
                const idx = list.findIndex((x) => x?.id === tempId);
                if (idx >= 0) list[idx] = data;
                draft.items = list;
                recalcCartTotals(draft);
              }),
            );
          }
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    updateCartItem: builder.mutation({
      query: ({ itemId, ...payload }) => ({
        url: `/api/v1/cart/items/${encodeURIComponent(String(itemId))}`,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      async onQueryStarted(
        { itemId, ...patchBody },
        { dispatch, queryFulfilled },
      ) {
        const nextQtyRaw = patchBody?.quantity;
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const idx = list.findIndex((x) => String(x?.id) === String(itemId));
            if (idx < 0) return;

            const nextQty = Number(nextQtyRaw);
            if (!Number.isFinite(nextQty) || nextQty < 0) return;

            if (nextQty === 0) {
              list.splice(idx, 1);
            } else {
              list[idx].quantity = nextQty;
              const price = Number(list[idx]?.product?.price);
              if (Number.isFinite(price)) {
                list[idx].line_total = price * nextQty;
              }
            }

            draft.items = list;
            recalcCartTotals(draft);
          }),
        );

        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),
    removeCartItem: builder.mutation({
      query: (itemId) => ({
        url: `/api/v1/cart/items/${encodeURIComponent(String(itemId))}`,
        method: "DELETE",
      }),
      async onQueryStarted(itemId, { dispatch, queryFulfilled }) {
        const patch = dispatch(
          api.util.updateQueryData("getMyCart", undefined, (draft) => {
            if (!draft || typeof draft !== "object") return;
            const list = Array.isArray(draft.items) ? draft.items : [];
            const next = list.filter((x) => String(x?.id) !== String(itemId));
            draft.items = next;
            recalcCartTotals(draft);
          }),
        );
        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
      invalidatesTags: ["Cart"],
    }),

    // Orders
    listOrders: builder.query({
      query: (userId) =>
        `/api/v1/orders/?user_id=${encodeURIComponent(String(userId))}`,
      providesTags: ["Orders"],
    }),
    getOrderById: builder.query({
      query: (orderId) =>
        `/api/v1/orders/${encodeURIComponent(String(orderId))}`,
      providesTags: (_result, _err, orderId) => [
        { type: "Orders", id: orderId },
      ],
    }),
    createOrder: builder.mutation({
      query: (payload) => ({
        url: "/api/v1/orders/",
        method: "POST",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: ["Orders", "Cart"],
    }),
    updateOrderStatus: builder.mutation({
      query: ({ orderId, ...payload }) => ({
        url: `/api/v1/orders/${encodeURIComponent(String(orderId))}/status`,
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: payload,
      }),
      invalidatesTags: (_result, _err, { orderId }) => [
        "Orders",
        { type: "Orders", id: orderId },
      ],
    }),
    getOrderStatus: builder.query({
      query: (orderId) =>
        `/api/v1/orders/${encodeURIComponent(String(orderId))}/status`,
      providesTags: (_result, _err, orderId) => [
        { type: "Orders", id: orderId },
      ],
    }),

    /* ================= Search ================= */

    getSearchSuggestions: builder.query({
      async queryFn(rawQuery, _api, _extraOptions, baseQuery) {
        const q = typeof rawQuery === "string" ? rawQuery.trim() : "";
        if (!q) return { data: [] };

        // Backend validation error shows it expects query param name `q`.
        // Keep a single request per keystroke to avoid 422 noise.
        const sp = new URLSearchParams();
        sp.set("q", q);

        // 1) GET /api/v1/search?q=...
        {
          const res = await baseQuery({
            url: `/api/v1/search?${sp.toString()}`,
            method: "GET",
          });
          if (res && !res.error) {
            const arr = Array.isArray(res.data)
              ? res.data
              : Array.isArray(res.data?.items)
                ? res.data.items
                : [];
            return { data: arr };
          }

          const st = res?.error?.status;
          // If backend doesn't support GET, try POST once.
          if (st != null && st !== 404 && st !== 405)
            return { error: res.error };
        }

        // 2) POST /api/v1/search {q}
        {
          const res = await baseQuery({
            url: "/api/v1/search",
            method: "POST",
            headers: { "content-type": "application/json" },
            body: { q },
          });
          if (res && !res.error) {
            const arr = Array.isArray(res.data)
              ? res.data
              : Array.isArray(res.data?.items)
                ? res.data.items
                : [];
            return { data: arr };
          }
          return { error: res?.error ?? { status: 404, data: null } };
        }
      },
      keepUnusedDataFor: 60,
    }),

    getSearchHistory: builder.query({
      async queryFn(_arg, _api, _extraOptions, baseQuery) {
        // Backend confirmed: history lives at /api/v1/ and supports ?limit=
        // Example: GET https://.../api/v1/?limit=10
        const res = await baseQuery({
          url: "/api/v1?limit=10",
          method: "GET",
        });
        if (res?.error) return { error: res.error };

        const data = res?.data;
        const items = Array.isArray(data)
          ? data
          : Array.isArray(data?.items)
            ? data.items
            : [];
        return { data: items };
      },
      providesTags: ["SearchHistory"],
      keepUnusedDataFor: 300,
    }),

    createSearchHistory: builder.mutation({
      async queryFn(payload, _api, _extraOptions, baseQuery) {
        const query =
          payload && typeof payload === "object" ? payload.query : "";
        const parameters =
          payload && typeof payload === "object" ? payload.parameters : {};

        const rawParams =
          parameters && typeof parameters === "object" ? parameters : {};
        const additionalProp1 =
          rawParams &&
          typeof rawParams === "object" &&
          rawParams.additionalProp1 &&
          typeof rawParams.additionalProp1 === "object"
            ? rawParams.additionalProp1
            : {};
        const wrappedParams = { additionalProp1 };

        const body = {
          query: typeof query === "string" ? query : String(query ?? ""),
          parameters: wrappedParams,
        };

        // Backend confirmed: create history via POST /api/v1/
        const res = await baseQuery({
          url: "/api/v1",
          method: "POST",
          headers: { "content-type": "application/json" },
          body,
        });

        if (res?.error) return { error: res.error };
        return { data: res?.data ?? null };
      },
      invalidatesTags: ["SearchHistory"],
      async onQueryStarted(payload, { dispatch, queryFulfilled }) {
        const query =
          payload && typeof payload === "object" ? payload.query : "";
        const parameters =
          payload && typeof payload === "object" ? payload.parameters : {};

        const rawParams =
          parameters && typeof parameters === "object" ? parameters : {};
        const additionalProp1 =
          rawParams &&
          typeof rawParams === "object" &&
          rawParams.additionalProp1 &&
          typeof rawParams.additionalProp1 === "object"
            ? rawParams.additionalProp1
            : {};
        const wrappedParams = { additionalProp1 };

        const tempItem = {
          id: -Date.now(),
          user_id: null,
          query: typeof query === "string" ? query : String(query ?? ""),
          parameters: wrappedParams,
          searched_at: new Date().toISOString(),
        };

        const patch = dispatch(
          api.util.updateQueryData("getSearchHistory", undefined, (draft) => {
            if (!Array.isArray(draft)) return;
            // Put on top, de-dup by normalized query string.
            const normalize = (v) =>
              String(v || "")
                .trim()
                .replace(/\s+/g, " ")
                .toLowerCase();
            const key = normalize(tempItem.query);
            const next = [
              tempItem,
              ...draft.filter((x) => normalize(x?.query) !== key),
            ];
            draft.splice(0, draft.length, ...next);
          }),
        );

        try {
          await queryFulfilled;
        } catch {
          patch.undo();
        }
      },
    }),
  }),
});

export const {
  useInitTelegramSessionMutation,
  useGetMeQuery,
  useGetProductsQuery,
  useLazyGetProductsQuery,
  useGetProductByIdQuery,
  useGetProductsByIdsQuery,
  useGetLatestProductsQuery,
  useGetLatestPurchasedProductsQuery,
  useGetCategoriesQuery,
  useCreateCategoryMutation,
  useDeleteCategoryMutation,
  useGetCategoriesWithTypesQuery,
  useGetTypesByCategoryQuery,
  useCreateTypeMutation,
  useUpdateTypeMutation,
  useDeleteTypeMutation,
  useGetBrandsQuery,
  useSearchBrandsQuery,
  useGetBrandByIdQuery,
  useCreateBrandMutation,
  useDeleteBrandMutation,
  useUploadBrandLogoMutation,
  useDeleteBrandLogoMutation,
  useGetFavoritesQuery,
  useAddFavoriteMutation,
  useRemoveFavoriteMutation,
  useGetMyReferralLinkQuery,
  useGetMyInvitedUsersQuery,
  useGetMyActiveDiscountQuery,
  useGetMyReferralStatsQuery,
  useGetMyCartQuery,
  useClearCartMutation,
  useAddCartItemMutation,
  useUpdateCartItemMutation,
  useRemoveCartItemMutation,
  useListOrdersQuery,
  useGetOrderByIdQuery,
  useCreateOrderMutation,
  useUpdateOrderStatusMutation,
  useGetOrderStatusQuery,
  useGetSearchSuggestionsQuery,
  useGetSearchHistoryQuery,
  useCreateSearchHistoryMutation,
} = api;
