'use client';

import { use } from 'react';

import OrderDetailsClient from '../../[id]/OrderDetailsClient';

export default function ReceivedOrderDetailsPage({ params }) {
  const { id } = use(params);
  return <OrderDetailsClient id={id} variant="received" />;
}
