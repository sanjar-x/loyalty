'use client';

import { useMemo } from 'react';

import { useGetFavoriteListsQuery, useCreateFavoriteListMutation } from '@/lib/store/api';
import { useAuthStore } from '@/lib/features/auth/store';
import { AuthStatus } from '@/lib/features/auth/types';

/**
 * Userning sevimli kollektsiyalari (FavoriteList) bilan ishlash uchun
 * yagona kirish. Backend har autentifikatsiyalangan callerga `is_default:
 * true` bo'lgan default list ni avtomatik berishi kutiladi (server
 * lazy-create). Agar shu yo'q bo'lsa — frontend "Избранное" nomli yangi
 * list ochib oladi va shu ID ni qaytaradi (best-effort, ikkinchi tashrifda
 * cache'dan keladi).
 *
 * Auth gate: agar caller `AUTHENTICATED` emas — query skip, hook bo'sh
 * data qaytaradi. Boshqa hook'lar (useItemFavorites) shu signal'ga
 * tayanib bulk check va items query'larni shartli yoqadi.
 */
export function useFavoriteLists() {
  const isAuthenticated = useAuthStore((s) => s.status === AuthStatus.AUTHENTICATED);

  const {
    data: lists,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useGetFavoriteListsQuery(undefined, { skip: !isAuthenticated });

  const items = useMemo(() => (Array.isArray(lists) ? lists : []), [lists]);

  const defaultList = useMemo(() => {
    if (!items.length) return null;
    return items.find((l) => l && l.is_default === true) ?? items[0] ?? null;
  }, [items]);

  return {
    lists: items,
    defaultList,
    defaultListId: defaultList?.id ?? null,
    isAuthenticated,
    isLoading,
    isFetching,
    isError,
    refetch,
  };
}

/**
 * Convenience: faqat default list ID ni xohlovchi caller'lar uchun
 * (toggle handler default list'ga qo'shadi). Auth bo'lmasa `null`.
 */
export function useDefaultFavoriteListId() {
  return useFavoriteLists().defaultListId;
}

/**
 * Imperative "ensure default list exists" — agar backend lazy-create
 * qilmagan bo'lsa, "Избранное" nomli yangi list ochib uning ID'sini
 * qaytaradi. Konkurent chaqiruvlar refetch ko'rib bir-birini bosib
 * o'tmaydi (server tomondagi unique constraint shart).
 */
export function useEnsureDefaultList() {
  const { defaultListId, lists, refetch } = useFavoriteLists();
  const [createList] = useCreateFavoriteListMutation();

  return async function ensure() {
    if (defaultListId) return defaultListId;
    if (Array.isArray(lists) && lists.length > 0) {
      return lists[0]?.id ?? null;
    }
    try {
      const created = await createList({
        createFavoriteListRequest: { name: 'Избранное' },
      }).unwrap();
      const id = created?.id ?? null;
      // Cache'da is_default flagi ko'rinmagunicha qisqa refetch.
      try {
        await refetch?.()?.catch?.(() => null);
      } catch {
        // ignore
      }
      return id;
    } catch {
      return null;
    }
  };
}
