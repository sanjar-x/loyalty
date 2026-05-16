'use client';

import { use } from 'react';

import OrderDetailsClient from '../../[id]/OrderDetailsClient';

export default function CancelledOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsClient id={id} variant="cancelled" />;
}
