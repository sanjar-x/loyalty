'use client';

import { use } from 'react';

import ProductPageClient from './ProductPageClient';

/**
 * Client-only product page — hech qanday SSR fetch yo'q.
 * Slug `params` dan `use()` bilan olinadi; product ma'lumoti
 * client'da RTK Query (`useGetProductByIdQuery`) orqali JSON
 * request/response shaklida olinadi.
 */
export default function ProductPage({ params }) {
  const { slug } = use(params);
  return <ProductPageClient slug={slug} />;
}
