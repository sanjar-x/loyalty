'use client';

import { use } from 'react';

import OrderDetailsClient from '../../[id]/OrderDetailsClient';

export default function InTransitOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsClient id={id} variant="inTransit" />;
}
