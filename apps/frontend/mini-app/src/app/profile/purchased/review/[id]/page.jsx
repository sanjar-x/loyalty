'use client';

import { use } from 'react';

import ReviewPage from '@/widgets/ReviewPage/ReviewPage';

export default function Route({ params }) {
  const { id } = use(params);
  return <ReviewPage id={id} />;
}
