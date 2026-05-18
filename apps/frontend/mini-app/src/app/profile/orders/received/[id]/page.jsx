'use client';

import { use } from 'react';

import OrderDetailsPage from '@/widgets/OrderDetailsPage/OrderDetailsPage';

export default function ReceivedOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsPage id={id} variant="received" />;
}
