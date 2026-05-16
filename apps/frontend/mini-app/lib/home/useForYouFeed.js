'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useGetForYouFeedQuery, useLazyGetForYouFeedQuery } from '@/lib/store/api';
import { mapProductCard } from '@/lib/adapters/mapProductCard';

/**
 * Bosh sahifa "Для вас" personalizatsiyalangan feed — cursor-paginatsiya,
 * IntersectionObserver infinite-scroll, transient xatoda exponential-backoff
 * auto-retry. Audit #1: `app/page.jsx` god-komponentidan ajratildi (~150 satr).
 *
 * `sentinelRef` chiqarib beriladi — sahifa uni feed oxiridagi `<div>`'ga
 * biriktiradi. IntersectionObserver faqat `isHomeMode` da faollashadi.
 *
 * @param {{ isHomeMode: boolean }} params
 */
const PAGE_SIZE = 10;
export const MAX_AUTO_RETRIES = 3;

export function useForYouFeed({ isHomeMode }) {
  const sentinelRef = useRef(null);

  const {
    data: initialProductsResponse,
    isLoading: isInitialProductsLoading,
    isFetching: isInitialProductsFetching,
  } = useGetForYouFeedQuery({ limit: PAGE_SIZE });

  const initialProductsItems = useMemo(() => {
    if (!initialProductsResponse) return [];
    return Array.isArray(initialProductsResponse.items) ? initialProductsResponse.items : [];
  }, [initialProductsResponse]);

  const [extraRecommendedRaw, setExtraRecommendedRaw] = useState([]);
  const [recommendedHasMore, setRecommendedHasMore] = useState(true);
  const [loadMoreError, setLoadMoreError] = useState(null);
  const retryAttemptsRef = useRef(0);
  const retryTimerRef = useRef(null);
  const [nextCursorRef] = useState(() => ({ current: null }));
  const [triggerGetForYou, forYouQuery] = useLazyGetForYouFeedQuery();

  // Sync initial response cursor
  useEffect(() => {
    if (initialProductsResponse?.nextCursor) {
      nextCursorRef.current = initialProductsResponse.nextCursor;
    }
    if (initialProductsResponse && !initialProductsResponse.hasNext) {
      setRecommendedHasMore(false);
    }
  }, [initialProductsResponse, nextCursorRef]);

  // Cancel any pending retry on unmount
  useEffect(() => {
    return () => {
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
    };
  }, []);

  const mergeUniqueById = useCallback((prev, next) => {
    const out = Array.isArray(prev) ? [...prev] : [];
    const seen = new Set(out.map((p) => p?.id).filter((id) => id != null));
    const rows = Array.isArray(next) ? next : [];
    for (const p of rows) {
      if (p?.id == null || seen.has(p.id)) continue;
      seen.add(p.id);
      out.push(p);
    }
    return out;
  }, []);

  const loadMoreRecommended = useCallback(async () => {
    if (!initialProductsItems.length) return;
    if (!recommendedHasMore) return;
    if (forYouQuery.isFetching) return;
    const cursor = nextCursorRef.current;
    if (!cursor) {
      setRecommendedHasMore(false);
      return;
    }
    try {
      const response = await triggerGetForYou({
        cursor,
        limit: PAGE_SIZE,
      }).unwrap();
      const arr = Array.isArray(response?.items) ? response.items : [];
      setExtraRecommendedRaw((prev) => mergeUniqueById(prev, arr));
      if (response?.nextCursor) {
        nextCursorRef.current = response.nextCursor;
      } else {
        nextCursorRef.current = null;
      }
      setRecommendedHasMore(Boolean(response?.hasNext));
      setLoadMoreError(null);
      retryAttemptsRef.current = 0;
    } catch (err) {
      // RTK Query errors: { status, data } — status may be a number (HTTP),
      // "FETCH_ERROR" (network), "TIMEOUT_ERROR", or "PARSING_ERROR".
      const status = err?.status;
      const isHttpStatus = typeof status === 'number';
      const isTransient =
        !isHttpStatus /* network / timeout / parsing */ ||
        (status >= 500 && status <= 599) ||
        status === 408 ||
        status === 429;

      if (isTransient && retryAttemptsRef.current < MAX_AUTO_RETRIES) {
        const attempt = retryAttemptsRef.current + 1;
        retryAttemptsRef.current = attempt;
        // Exponential backoff: 1s → 2s → 4s (with ±20% jitter)
        const base = 1000 * Math.pow(2, attempt - 1);
        const jitter = base * (0.8 + Math.random() * 0.4);
        const delay = Math.round(jitter);
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
        retryTimerRef.current = setTimeout(() => {
          retryTimerRef.current = null;
          // Re-trigger: cursor is unchanged (wasn't advanced on failure)
          loadMoreRecommended();
        }, delay);
        setLoadMoreError({ transient: true, attempt });
        return;
      }

      // Auto-retries exhausted OR non-transient (4xx except 408/429):
      // surface error UI, keep cursor intact so user can manually retry.
      setLoadMoreError({
        transient: isTransient,
        attempt: retryAttemptsRef.current,
        exhausted: true,
      });
    }
  }, [
    initialProductsItems,
    mergeUniqueById,
    forYouQuery.isFetching,
    recommendedHasMore,
    triggerGetForYou,
    nextCursorRef,
  ]);

  const retryLoadMore = useCallback(() => {
    retryAttemptsRef.current = 0;
    setLoadMoreError(null);
    loadMoreRecommended();
  }, [loadMoreRecommended]);

  useEffect(() => {
    if (!isHomeMode) return;
    const el = sentinelRef.current;
    if (!el) return;
    if (!initialProductsItems.length) return;
    if (!recommendedHasMore) return;
    // Don't re-trigger while an error is surfaced — user must click "Повторить"
    // (or the auto-retry timer will call loadMoreRecommended directly).
    if (loadMoreError?.exhausted) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMoreRecommended();
      },
      { root: null, rootMargin: '200px', threshold: 0.01 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [
    initialProductsItems,
    isHomeMode,
    loadMoreRecommended,
    recommendedHasMore,
    loadMoreError?.exhausted,
  ]);

  const recommendedProducts = useMemo(() => {
    const extraArr = Array.isArray(extraRecommendedRaw) ? extraRecommendedRaw : [];
    const merged = mergeUniqueById(initialProductsItems, extraArr);
    return merged.map((p) => mapProductCard(p, null)).filter(Boolean);
  }, [extraRecommendedRaw, initialProductsItems, mergeUniqueById]);

  const isRecommendedInitialLoading =
    (isInitialProductsLoading || isInitialProductsFetching) && initialProductsItems.length === 0;

  const isRecommendedLoadingMore = forYouQuery.isFetching && initialProductsItems.length > 0;
  const isRecommendedRetryPending =
    !!loadMoreError &&
    !loadMoreError.exhausted &&
    loadMoreError.transient &&
    !forYouQuery.isFetching;

  return {
    recommendedProducts,
    sentinelRef,
    isRecommendedInitialLoading,
    isRecommendedLoadingMore,
    isRecommendedRetryPending,
    loadMoreError,
    retryLoadMore,
  };
}
