import { ordersSeed } from '@/data/orders';

let orders = [...ordersSeed];

export function getOrders() {
  return [...orders];
}

export function getOrderById(id) {
  return orders.find((order) => order.id === id) ?? null;
}

export async function updateOrderStatus(orderId, status) {
  orders = orders.map((order) =>
    order.id === orderId ? { ...order, status } : order,
  );
  return orders.find((order) => order.id === orderId);
}
