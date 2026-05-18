'use client';

import { use } from 'react';

import OrderDetailsPage from '@/widgets/OrderDetailsPage/OrderDetailsPage';

export default function InTransitOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsPage id={id} variant="inTransit" />;
}
