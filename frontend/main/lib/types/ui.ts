export interface ProductCardData {
  id: number | string;
  name: string;
  price: string;
  image: string;
  imageFallbacks?: string[];
  isFavorite?: boolean;
  brand?: string;
  deliveryText?: string;
  rating?: number;
  installment?: string;
  deliveryDate?: string;
}
