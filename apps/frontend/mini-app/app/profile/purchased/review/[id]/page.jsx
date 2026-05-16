'use client';

import { use } from 'react';

import ReviewClient from './ReviewClient';

export default function ReviewPage({ params }) {
  const { id } = use(params);
  return <ReviewClient id={id} />;
}
