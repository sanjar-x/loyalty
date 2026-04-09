'use client';

import { useCallback, useEffect, useMemo, useRef } from 'react';

import { useInfiniteQuery } from '@tanstack/react-query';

import { Skeleton } from '@/components/ui/skeleton';
import { ProductCard } from '@/features/product/components/product-card';
import { apiClient } from '@/lib/api-client';
import { formatRub } from '@/lib/format/price';
import { getProductPhotoCandidates } from '@/lib/format/product-image';
import { queryKeys } from '@/lib/query-keys';
import { cn } from '@/lib/utils';
import type { PaginatedResponse, Product, ProductCardData } from '@/types';

// ── Constants ───────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ── Helpers ─────────────────────────────────────────────────────────

/** Map an API Product to the shape the ProductCard component expects. */
function toCardData(product: Product): ProductCardData {
  const candidates = getProductPhotoCandidates(product);
  const name =
    product.titleI18n?.ru ?? product.titleI18n?.en ?? Object.values(product.titleI18n ?? {})[0] ?? '';

  return {
    id: product.id,
    name: String(name),
    price: formatRub(product.price),
    image: candidates[0] ?? '',
    imageFallbacks: candidates.slice(1),
  };
}

// ── Types ───────────────────────────────────────────────────────────

interface ProductGridProps {
  categoryId?: string | null;
  className?: string;
}

// ── Component ───────────────────────────────────────────────────────

export function ProductGrid({ categoryId, className }: ProductGridProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey: [
      ...queryKeys.products.lists(),
      'infinite',
      { category_id: categoryId ?? undefined },
    ],
    queryFn: async ({ pageParam = 0 }) => {
      const searchParams: Record<string, string> = {
        skip: String(pageParam),
        limit: String(PAGE_SIZE),
      };
      if (categoryId) {
        searchParams.category_id = categoryId;
      }
      return apiClient
        .get('api/v1/products/', { searchParams })
        .json<PaginatedResponse<Product>>();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const fetched = allPages.reduce((sum, p) => sum + p.items.length, 0);
      if (lastPage.items.length < PAGE_SIZE) return undefined;
      if (fetched >= lastPage.total) return undefined;
      return fetched;
    },
  });

  // IntersectionObserver for infinite scroll
  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      const [entry] = entries;
      if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
        void fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage],
  );

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(handleIntersect, {
      root: null,
      rootMargin: '300px',
      threshold: 0.01,
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [handleIntersect]);

  const cards = useMemo(
    () => (data?.pages.flatMap((page) => page.items) ?? []).map(toCardData),
    [data],
  );

  // No-op toggle — favorites integration will be connected separately
  const handleToggleFavorite = useCallback(() => {}, []);

  // Initial loading state
  if (isLoading) {
    return (
      <div className={cn('grid grid-cols-2 gap-2 px-4', className)}>
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-64 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (cards.length === 0) {
    return (
      <div className="px-4 py-12 text-center">
        <p className="text-sm text-gray-400">Товары не найдены</p>
      </div>
    );
  }

  return (
    <div className={cn('px-4', className)}>
      <div className="grid grid-cols-2 gap-2">
        {cards.map((card) => (
          <ProductCard
            key={card.id}
            product={card}
            onToggleFavorite={handleToggleFavorite}
          />
        ))}
      </div>

      {/* Loading more indicator */}
      {isFetchingNextPage && (
        <div className="flex items-center justify-center gap-2 py-6">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
          <span className="text-xs text-gray-400">Загрузка...</span>
        </div>
      )}

      {/* Intersection observer sentinel */}
      <div ref={sentinelRef} className="h-px" aria-hidden />
    </div>
  );
}
