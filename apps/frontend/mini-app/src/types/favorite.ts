export interface Favorite {
  id: string;
  userId: string;
  itemId: string;
  itemType: string;
  brandId?: string;
  createdAt: string;
}

export interface AddFavoritePayload {
  item_id: string;
  item_type: string;
  brand_id?: string;
}
