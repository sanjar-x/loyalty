'use client';

import { use } from 'react';

import ReturnRequestPage from '@/widgets/ReturnRequestPage/ReturnRequestPage';

export default function Route({ params }) {
  const { id } = use(params);
  return <ReturnRequestPage id={id} />;
}
