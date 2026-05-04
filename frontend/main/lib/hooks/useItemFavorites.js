import { useCallback, useMemo, useRef, useState } from "react";
import { useDispatch } from "react-redux";

import {
  api,
  useAddFavoriteMutation,
  useGetFavoritesQuery,
  useRemoveFavoriteMutation,
} from "@/lib/store/api";
import { useAuthStore } from "@/lib/features/auth/store";
import { AuthStatus } from "@/lib/features/auth/types";

function toPositiveInt(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? Math.trunc(n) : null;
}

export function useItemFavorites(itemType) {
  const type = itemType === "brand" ? "brand" : "product";
  const dispatch = useDispatch();

  const [optimisticMap, setOptimisticMap] = useState(() => new Map());
  const pendingItemIdsRef = useRef(new Set());

  const authStatus = useAuthStore((s) => s.status);
  const isAuthenticated = authStatus === AuthStatus.AUTHENTICATED;

  // Backend user identity'ni `Authorization: Bearer <token>` header orqali
  // aniqlaydi — `user_id` payloadda yuborish ortiqcha. Shu sababli `/me`
  // uchun alohida request yubormaymiz; user ma'lumoti kerak bo'lsa
  // Zustand auth store'dagi `user` ob'ektidan olinadi.

  const {
    data: favoritesRaw,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetFavoritesQuery({ item_type: type }, { skip: !isAuthenticated });

  const favorites = useMemo(
    () => (Array.isArray(favoritesRaw) ? favoritesRaw : []),
    [favoritesRaw],
  );

  const itemIdToFavoriteIds = useMemo(() => {
    const map = new Map();
    for (const f of favorites) {
      if (!f || typeof f !== "object") continue;
      const favoriteId = toPositiveInt(f.id);
      if (favoriteId == null) continue;
      const itemId =
        type === "brand"
          ? toPositiveInt(f.brand_id)
          : toPositiveInt(f.product_id);
      if (itemId == null) continue;
      const arr = map.get(itemId) ?? [];
      arr.push(favoriteId);
      map.set(itemId, arr);
    }
    return map;
  }, [favorites, type]);

  const favoriteItemIds = useMemo(
    () => new Set(Array.from(itemIdToFavoriteIds.keys())),
    [itemIdToFavoriteIds],
  );

  const effectiveFavoriteItemIds = useMemo(() => {
    if (!optimisticMap.size) return favoriteItemIds;
    const out = new Set(favoriteItemIds);
    for (const [itemId, desired] of optimisticMap.entries()) {
      if (desired) out.add(itemId);
      else out.delete(itemId);
    }
    return out;
  }, [favoriteItemIds, optimisticMap]);

  const [addFavorite, addState] = useAddFavoriteMutation();
  const [removeFavorite, removeState] = useRemoveFavoriteMutation();

  const isMutating = Boolean(addState.isLoading || removeState.isLoading);

  const toggleFavorite = useCallback(
    async (rawItemId) => {
      const itemId = toPositiveInt(rawItemId);
      if (itemId == null) return;

      // Prevent rapid double toggles on the same item while request is in-flight.
      if (pendingItemIdsRef.current.has(itemId)) return;

      const currentlyFavorite = effectiveFavoriteItemIds.has(itemId);
      const nextDesired = !currentlyFavorite;

      // Instant UI feedback
      setOptimisticMap((prev) => {
        const next = new Map(prev);
        next.set(itemId, nextDesired);
        return next;
      });

      pendingItemIdsRef.current.add(itemId);

      try {
        const existingFavoriteIds = itemIdToFavoriteIds.get(itemId) ?? [];

        if (!nextDesired) {
          // Backend может содержать дубликаты — чистим все записи.
          await Promise.all(
            existingFavoriteIds.map((fid) =>
              removeFavorite(fid)
                .unwrap()
                .catch(() => null),
            ),
          );

          if (type === "product") {
            dispatch(
              api.util.invalidateTags([{ type: "Product", id: itemId }]),
            );
          }

          await refetch?.().catch?.(() => null);

          setOptimisticMap((prev) => {
            if (!prev.size) return prev;
            const next = new Map(prev);
            next.delete(itemId);
            return next;
          });

          return;
        }

        const payload =
          type === "brand"
            ? { brand_id: itemId }
            : { product_id: itemId };

        await addFavorite(payload)
          .unwrap()
          .catch(() => null);

        if (type === "product") {
          dispatch(api.util.invalidateTags([{ type: "Product", id: itemId }]));
        }

        await refetch?.().catch?.(() => null);

        setOptimisticMap((prev) => {
          if (!prev.size) return prev;
          const next = new Map(prev);
          next.delete(itemId);
          return next;
        });
      } finally {
        pendingItemIdsRef.current.delete(itemId);
      }
    },
    [
      addFavorite,
      dispatch,
      effectiveFavoriteItemIds,
      itemIdToFavoriteIds,
      refetch,
      removeFavorite,
      type,
    ],
  );

  return {
    favorites,
    favoriteItemIds: effectiveFavoriteItemIds,
    itemIdToFavoriteIds,
    toggleFavorite,
    isLoading,
    isFetching,
    isError,
    isMutating,
    refetch,
  };
}
