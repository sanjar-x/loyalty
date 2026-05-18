'use client';

import { use } from 'react';

import ProductPage from '@/widgets/ProductPage/ProductPage';

/**
 * Client-only product page — no SSR fetch at all.
 * The slug is taken from `params` with `use()`; the product data is
 * fetched on the client via RTK Query (`useGetProductByIdQuery`) as a
 * plain JSON request/response.
 */
export default function Route({ params }) {
  const { slug } = use(params);
  return <ProductPage slug={slug} />;
}
