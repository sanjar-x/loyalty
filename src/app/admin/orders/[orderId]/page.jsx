import { notFound } from 'next/navigation';
import { OrderDetailsView } from '@/components/admin/OrderDetailsView';
import { getOrderById } from '@/services/orders';

export default async function OrderDetailsPage({ params }) {
  const { orderId } = await params;
  const order = getOrderById(orderId);

  if (!order) {
    notFound();
  }

  return <OrderDetailsView order={order} />;
}

