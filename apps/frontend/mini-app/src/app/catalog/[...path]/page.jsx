'use client';

import { use } from 'react';

import CategoryPage from '@/widgets/CategoryPage/CategoryPage';

function safeDecodeSegment(s) {
  try {
    return decodeURIComponent(String(s ?? ''));
  } catch {
    return String(s ?? '');
  }
}

export default function Route({ params }) {
  const { path } = use(params);
  const segments = Array.isArray(path) ? path.map(safeDecodeSegment) : [];
  return <CategoryPage segments={segments} />;
}
