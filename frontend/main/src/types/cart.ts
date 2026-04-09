export interface CartItem {
  id: string;
  productId: string;
  skuId: string;
  quantity: number;
  price: number;
  name?: string;
  image?: string;
  size?: string;
  article?: string;
  brand?: string;
  deliveryText?: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalItems: number;
  totalAmount: number;
}
