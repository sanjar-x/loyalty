import { notFound } from 'next/navigation';
import { OrderDetailsView } from '@/entities/order';
import { getOrderById } from '@/entities/order';

export default async function OrderDetailsPage({ params }) {
  const { orderId } = await params;
  const order = getOrderById(orderId);

  if (!order) {
    notFound();
  }

  return <OrderDetailsView order={order} />;
}
