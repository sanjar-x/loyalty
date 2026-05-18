/** Sprint 3d: Favorite RTKQ hooks. */
import { enhancedApi, customApi } from '@/app/providers/store/instance';

export const useGetFavoriteListsQuery =
  enhancedApi.useListFavoriteListsApiV1FavoritesListsGetQuery;
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
