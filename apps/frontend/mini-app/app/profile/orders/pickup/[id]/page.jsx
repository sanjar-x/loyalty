'use client';

import { use } from 'react';

import OrderDetailsClient from '../../[id]/OrderDetailsClient';

export default function PickupOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsClient id={id} variant="pickup" />;
}
