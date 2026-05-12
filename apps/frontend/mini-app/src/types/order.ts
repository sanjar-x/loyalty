export type OrderStatus =
  | "pending"
  | "confirmed"
  | "processing"
  | "shipped"
  | "in_transit"
  | "delivered"
  | "pickup_ready"
  | "received"
  | "cancelled"
  | "returned";

export interface Order {
  id: string;
  userId: string;
  status: OrderStatus;
  items: OrderItem[];
  totalAmount: number;
  shippingAddress?: string;
  pickupPointId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface OrderItem {
  id: string;
  productId: string;
  skuId: string;
  quantity: number;
  price: number;
  name: string;
  image?: string;
  size?: string;
}
