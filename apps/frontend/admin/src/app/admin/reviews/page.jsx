'use client';

import { Suspense, useMemo, useState, useEffect } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import dayjs from '@/shared/lib/dayjs';
import {
  ReviewCard,
  PillSelect,
  RatingSummary,
  ReviewsPageFallback,
  getReviews,
} from '@/entities/review';
import { Pagination } from '@/shared/ui/Pagination';
import styles from './page.module.css';

function ReviewsPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [reviews, setReviews] = useState(() => getReviews());
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  const sort = searchParams.get('sort') ?? 'newest';
  const rating = searchParams.get('rating') ?? 'all';
  const pageParam = searchParams.get('page') ?? '1';
  const page = Math.max(1, Number.parseInt(pageParam, 10) || 1);

  function setQuery(next) {
    const params = new URLSearchParams(searchParams);
    Object.entries(next).forEach(([key, value]) => {
      if (!value || value === 'default') {
        params.delete(key);
        return;
      }
      params.set(key, String(value));
    });

    const queryString = params.toString();
    router.push(queryString ? `${pathname}?${queryString}` : pathname);
  }

  const ratingOptions = useMemo(
    () => [
      { value: 'all', label: 'Все оценки' },
      { value: '5', label: '5' },
      { value: '4', label: '4' },
      { value: '3', label: '3' },
      { value: '2', label: '2' },
      { value: '1', label: '1' },
    ],
    [],
  );

  const sortOptions = useMemo(
    () => [
      { value: 'newest', label: 'Сначала новые' },
      { value: 'oldest', label: 'Сначала старые' },
    ],
    [],
  );

  const scopeOptions = useMemo(
    () => [
      {
        value: 'all',
        label: 'Все',
        suffix: `${reviews.length.toLocaleString('ru-RU')}`,
      },
    ],
    [reviews.length],
  );

  const filtered = useMemo(() => {
    let next = reviews.slice();

    if (rating !== 'all') {
      const target = Number.parseInt(rating, 10);
      if (target >= 1 && target <= 5) {
        next = next.filter((r) => Number(r.rating) === target);
      }
    }

    next.sort((a, b) => {
      const left = dayjs(a.createdAt).valueOf();
      const right = dayjs(b.createdAt).valueOf();
      return sort === 'oldest' ? left - right : right - left;
    });

    return next;
  }, [rating, reviews, sort]);

  const perPage = 3;
  const pages = Math.max(1, Math.ceil(filtered.length / perPage));
  const pageSafe = Math.min(page, pages);
  const visible = useMemo(
    () => filtered.slice((pageSafe - 1) * perPage, pageSafe * perPage),
    [filtered, pageSafe],
  );

  useEffect(() => {
    if (page !== pageSafe) {
      setQuery({ page: String(pageSafe) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSafe]);

  const reset = () => {
    router.push(pathname);
  };

  const toggleExpanded = (id) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const deleteReview = (id) => {
    setReviews((prev) => prev.filter((r) => r.id !== id));
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Отзывы</h1>

          <div className={styles.filters}>
            <PillSelect
              value="all"
              options={scopeOptions}
              onChange={() => {}}
              ariaLabel="Фильтр отзывов"
            />

            <PillSelect
              value={sort}
              options={sortOptions}
              onChange={(nextSort) => setQuery({ sort: nextSort, page: '1' })}
              ariaLabel="Сортировка"
            />

            <PillSelect
              value={rating}
              options={ratingOptions}
              label="Оценка"
              onChange={(nextRating) =>
                setQuery({ rating: nextRating, page: '1' })
              }
              ariaLabel="Фильтр по оценке"
            />

            <button
              type="button"
              onClick={reset}
              className={styles.resetButton}
              aria-label="Сбросить фильтры"
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 15 15"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M1 1L7.5 7.5M14 14L7.5 7.5M7.5 7.5L13.5357 1M7.5 7.5L1 14"
                  stroke="#2D2D2D"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          </div>
        </div>

        <RatingSummary reviews={filtered} />
      </div>

      <div className={styles.list}>
        {visible.length ? (
          visible.map((r) => {
            const expanded = expandedIds.has(r.id);
            const orderOrigin = (r.product?.tags ?? []).find(
              (t) => t === 'Из Китая' || t === 'Из наличия',
            );

            return (
              <ReviewCard
                key={r.id}
                product={{
                  brandName: r.product?.brand,
                  image: r.product?.image,
                  title: r.product?.title,
                  size: r.product?.size,
                }}
                review={{
                  rating: r.rating,
                  dateLabel: r.createdAt
                    ? dayjs(r.createdAt).format('D MMMM')
                    : '',
                  pros: r.pros,
                  cons: r.cons,
                  comment: r.comment,
                  user: {
                    name: r.user?.name,
                    avatar: r.user?.avatarUrl || r.user?.avatar || '',
                  },
                }}
                order={{
                  id: r.order?.id,
                  number: r.order?.number,
                  dateLabel: r.order?.createdAt
                    ? dayjs(r.order.createdAt).format('D MMMM')
                    : '',
                  originLabel: orderOrigin,
                }}
                expanded={expanded}
                onOpenOrder={(order) =>
                  router.push(`/admin/orders/${order?.id || r.order?.id}`)
                }
                onDelete={() => deleteReview(r.id)}
                onToggleExpand={() => toggleExpanded(r.id)}
              />
            );
          })
        ) : (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Отзывы не найдены</p>
            <p className={styles.emptyText}>Попробуйте изменить фильтры.</p>
          </div>
        )}
      </div>

      <Pagination
        page={pageSafe}
        pages={pages}
        onPage={(nextPage) => setQuery({ page: String(nextPage) })}
      />
    </section>
  );
}

export default function ReviewsPage() {
  return (
    <Suspense fallback={<ReviewsPageFallback />}>
      <ReviewsPageContent />
    </Suspense>
  );
}
