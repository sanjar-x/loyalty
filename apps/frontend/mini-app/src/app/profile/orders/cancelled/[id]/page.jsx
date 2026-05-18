'use client';

import { use } from 'react';

import OrderDetailsPage from '@/widgets/OrderDetailsPage/OrderDetailsPage';

export default function CancelledOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsPage id={id} variant="cancelled" />;
}
