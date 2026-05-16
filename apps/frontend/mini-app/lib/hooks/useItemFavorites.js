'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';

import {
  api,
  useAddFavoriteItemMutation,
  useListFavoriteItemsQuery,
  useRemoveFavoriteItemMutation,
} from '@/lib/store/api';
import { useFavoriteLists } from '@/lib/hooks/useFavoriteLists';
import { humanizeApiError } from '@/lib/api/errors';
import { toast } from '@/lib/ui/toast';

/** Telegram WebApp tactile feedback — tugma bosilganda fizik signal beradi.
 *  Tarmoq javobini kutmasdan foydalanuvchi "tugma ishladi" hissini oladi.
 *  Hech qanday Telegram client'da bo'lmagan muhitda no-op (browser dev). */
function tactileBounce() {
  if (typeof window === 'undefined') return;
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('light');
  } catch {
    // ignore — non-Telegram host
  }
}

/**
 * v1 favorites contract bilan ishlovchi hook.
 *
 * Domain mapping:
 *  • `targetType` ∈ ["product", "brand"] — backend `FavoriteTargetType` enum.
 *  • `targetId` — UUID string (catalog Product.id / Brand.id).
 *  • Backend bitta default `FavoriteList`'ni har callerga avtomatik beradi.
 *    Add request'da `list_id` berilmasa server uni o'zi default listga
 *    biriktiradi — frontend lazy-create logikasini bu yerda qilmaymiz.
 *
 * Returns API (legacy contract bilan mos):
 *  • `favoriteItemIds: Set<string>` — favorited target_id'lar to'plami.
 *    Sahifalar `favoriteItemIds.has(target.id)` shaklida heart icon'ni
 *    boshqaradi. Optimistic toggle effekti shu Set'da darhol aks etadi.
 *  • `favorites: FavoriteItemResponse[]` — list ichidagi xom itemlar
 *    (enriched `product`/`brand` kartochka bilan).
 *  • `targetIdToFavoriteItem: Map<string, FavoriteItemResponse>` —
 *    target_id → item map. Sahifalar enriched kartochkani oluvchi sifatida
 *    saqlangan ma'lumot orqali render qilishi mumkin.
 *  • `toggleFavorite(targetId)` — UUID qabul qiladi. Hisobga olinmagan
 *    in-flight chaqiruvlar throttled (per-targetId ref-Set).
 *
 * Optimistic strategy:
 *  • Toggle bosilganda darhol `optimisticMap` Set'ga `targetId → desired`
 *    yoziladi. UI shu yerdan effective Set'ni ko'radi (server response'iga
 *    kutmaydi).
 *  • Mutation natijasi `Favorites` tag'larni invalidate qiladi → list
 *    items va bulk-check cache'lari refetch bo'ladi → optimistic patch
 *    olib tashlanadi.
 *  • Mutation fail bo'lsa optimistic patch tortib olinadi (UI eski
 *    holatga qaytadi). Throw qilmaymiz — UI toast uchun isError flag
 *    ekspoz qilinadi.
 *
 * Cheklov: hozir bir `useListFavoriteItemsQuery` bilan default list ichidan
 * `target_type` bo'yicha filtrlangan **birinchi sahifa** olinadi (limit: 100).
 * 100+ sevimli kerak bo'lsa cursor pagination qo'shish kerak.
 */
export function useItemFavorites(targetType) {
  const type = targetType === 'brand' ? 'brand' : 'product';
  const dispatch = useDispatch();

  const { defaultListId, isAuthenticated, isLoading: isListsLoading } = useFavoriteLists();

  const skipItemsQuery = !isAuthenticated || !defaultListId;

  const {
    data: itemsPage,
    isLoading: isItemsLoading,
    isFetching: isItemsFetching,
    isError,
    refetch,
  } = useListFavoriteItemsQuery(
    {
      listId: defaultListId,
      targetType: type,
      limit: 100,
    },
    { skip: skipItemsQuery }
  );

  const favorites = useMemo(
    () => (Array.isArray(itemsPage?.items) ? itemsPage.items : []),
    [itemsPage]
  );

  // target_id (UUID) → enriched FavoriteItemResponse. Sahifalar
  // mahsulot kartochkasi rasm/nomi uchun shu mapdan to'liq item oladi.
  const targetIdToFavoriteItem = useMemo(() => {
    const m = new Map();
    for (const it of favorites) {
      if (!it || typeof it !== 'object') continue;
      const tid = it.target_id;
      if (typeof tid !== 'string' || !tid) continue;
      m.set(tid, it);
    }
    return m;
  }, [favorites]);

  // target_id → list_id. Remove mutation 3 path-param talab qiladi —
  // listId ni shu map orqali topamiz (item turli listda bo'lishi
  // mumkin, faqat default'ni o'qiyapsak ham bu robust tutuvchi).
  const targetIdToListId = useMemo(() => {
    const m = new Map();
    for (const it of favorites) {
      if (!it || typeof it !== 'object') continue;
      const tid = it.target_id;
      const lid = it.list_id;
      if (typeof tid !== 'string' || typeof lid !== 'string') continue;
      m.set(tid, lid);
    }
    return m;
  }, [favorites]);

  const serverFavoriteIds = useMemo(
    () => new Set(targetIdToFavoriteItem.keys()),
    [targetIdToFavoriteItem]
  );

  // Optimistic patch: target_id → boolean (desired state).
  const [optimisticMap, setOptimisticMap] = useState(() => new Map());
  const inflightRef = useRef(new Set());

  const favoriteItemIds = useMemo(() => {
    if (!optimisticMap.size) return serverFavoriteIds;
    const out = new Set(serverFavoriteIds);
    for (const [tid, desired] of optimisticMap.entries()) {
      if (desired) out.add(tid);
      else out.delete(tid);
    }
    return out;
  }, [serverFavoriteIds, optimisticMap]);

  // Reconciliation: optimistic patch'ni server-side qiymat bilan
  // moslashtirib o'chirish. Mutation success'idan keyin RTKQ refetch
  // hali tugamagan bo'lishi mumkin — agar shu paytda optimistic'ni
  // o'chirsak, UI bir lahzaga eski holatga qaytadi (flicker). Shuning
  // o'rniga: optimistic patch'ni saqlab turib, server yangi qiymatni
  // qaytarganda (refetch tugadi va `serverFavoriteIds` desired qiymatga
  // teng bo'ldi) avtomatik o'chiramiz — UI hech qachon teskari aylanmaydi.
  useEffect(() => {
    if (optimisticMap.size === 0) return;
    setOptimisticMap((prev) => {
      let changed = false;
      const next = new Map(prev);
      for (const [tid, desired] of prev) {
        const serverHas = serverFavoriteIds.has(tid);
        if (serverHas === desired) {
          next.delete(tid);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverFavoriteIds]);

  const [addFavoriteItem, addState] = useAddFavoriteItemMutation();
  const [removeFavoriteItem, removeState] = useRemoveFavoriteItemMutation();

  const isMutating = Boolean(addState.isLoading || removeState.isLoading);

  const toggleFavorite = useCallback(
    async (rawTargetId) => {
      if (!isAuthenticated) {
        // Foydalanuvchi tizimga kirmagan — silent fail emas, toast bilan
        // ogohlantirish (loyihada Telegram-only auth, dev preview'da bu
        // yo'l ko'p uchraydi).
        toast.error('Войдите в аккаунт, чтобы добавлять в избранное');
        return;
      }

      const targetId =
        typeof rawTargetId === 'string'
          ? rawTargetId
          : rawTargetId == null
            ? ''
            : String(rawTargetId);
      if (!targetId) return;

      // Bir xil target uchun konkurent bosish — birinchisi tugamasdan
      // ikkinchisini boshlamaymiz (toggle ketma-ketligi siljib ketmasin).
      if (inflightRef.current.has(targetId)) return;

      const currentlyFavorite = favoriteItemIds.has(targetId);
      const nextDesired = !currentlyFavorite;

      // 1. Instant UI feedback (sync, render boshlanmasdan oldin):
      //    – optimistic Map yangilanadi (UI darhol o'zgaradi)
      //    – Telegram WebApp'da haptic bounce (fizik signal)
      tactileBounce();
      setOptimisticMap((prev) => {
        const next = new Map(prev);
        next.set(targetId, nextDesired);
        return next;
      });
      inflightRef.current.add(targetId);

      try {
        if (nextDesired) {
          // Add: list_id ixtiyoriy — server default listga biriktiradi.
          // `list_id` undefined bo'lsa property obyektga umuman qo'shilmaydi
          // → JSON.stringify uni o'tkazib yuboradi → server o'z default
          // list'iga biriktiradi (lazy-create). Bo'sh string / null
          // yubormaymiz — backend pattern uchun ortiqcha xato sababi.
          const body = {
            target_type: type,
            target_id: targetId,
          };
          if (defaultListId) body.list_id = defaultListId;

          try {
            await addFavoriteItem({ addFavoriteItemRequest: body }).unwrap();
          } catch (err) {
            // Rollback optimistic — server'da yo'q, UI ham `false`'ga.
            setOptimisticMap((prev) => {
              const next = new Map(prev);
              next.set(targetId, false);
              return next;
            });
            toast.error(humanizeApiError(err, 'Не удалось добавить в избранное'));
          }
        } else {
          const listId = targetIdToListId.get(targetId) ?? defaultListId;
          if (!listId) {
            // Hech qanday list ID topilmasa — server hali default list
            // yaratmagan. Optimistic patchni bekor qilib chiqamiz.
            setOptimisticMap((prev) => {
              if (!prev.has(targetId)) return prev;
              const next = new Map(prev);
              next.delete(targetId);
              return next;
            });
            return;
          }
          try {
            await removeFavoriteItem({
              listId,
              targetType: type,
              targetId,
            }).unwrap();
          } catch (err) {
            setOptimisticMap((prev) => {
              const next = new Map(prev);
              next.set(targetId, true);
              return next;
            });
            toast.error(humanizeApiError(err, 'Не удалось убрать из избранного'));
          }
        }

        // PDP cache invalidatsiyasi — `is_favorite` denormal field bo'lsa
        // server'dan yangi qiymat keladi (hozirgi backend'da yo'q, lekin
        // kelgusiga zaxira). Optimistic patch'ni bu yerda olib tashlamaymiz —
        // useEffect reconciliation server `serverFavoriteIds` yangilanganda
        // o'zi tozalaydi (UI flicker'ni oldini oluvchi yagona joy).
        if (type === 'product') {
          dispatch(api.util.invalidateTags([{ type: 'Product', id: targetId }]));
        }
      } finally {
        inflightRef.current.delete(targetId);
      }
    },
    [
      addFavoriteItem,
      defaultListId,
      dispatch,
      favoriteItemIds,
      isAuthenticated,
      removeFavoriteItem,
      targetIdToListId,
      type,
    ]
  );

  return {
    favorites,
    favoriteItemIds,
    targetIdToFavoriteItem,
    targetIdToListId,
    toggleFavorite,
    isLoading: Boolean(isListsLoading || isItemsLoading),
    isFetching: Boolean(isItemsFetching),
    isError,
    isMutating,
    refetch,
  };
}
