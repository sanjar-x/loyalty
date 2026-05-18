'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import Footer from '@/widgets/Footer';
import Header from '@/widgets/Header';
import { useListOrdersQuery } from '@/entities/order';
import { formatRub } from '@/shared/lib/money';
import styles from './page.module.css';

function pluralizeRu(n, one, few, many) {
  const x = Math.abs(Number(n)) % 100;
  const x1 = x % 10;
  if (x > 10 && x < 20) return many;
  if (x1 > 1 && x1 < 5) return few;
  if (x1 === 1) return one;
  return many;
}

function StatusHeader({ title, progress }) {
  return (
    <div className={`${styles.statusRow}`}>
      <div className={styles.statusLeft}>
        <div
          className={`${styles.statusTitle} ${title == 'Отменён' ? `${styles.makeGrey}` : ''} ${title == 'Получен' ? `${styles.makeGrey}` : ''}`}
        >
          {title}
          <img src="/icons/global/small-arrow.svg" alt="" className={styles.chevron} />
        </div>
        {progress ? (
          <div
            className={`${styles.statusProgress} ${title == 'Отменён' ? `${styles.makeGrey}` : ''} ${title == 'Получен' ? `${styles.makeGrey}` : ''}`}
          >
            {progress}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ProductThumb({ src, muted = false }) {
  return (
    <div className={styles.thumbWrap}>
      <img src={src} alt="" className={muted ? styles.thumbMuted : styles.thumb} loading="lazy" />
    </div>
  );
}

const REVIEW_PRODUCTS_KEY = 'lm:reviewProducts';

function clampRating(value) {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return 0;
  return Math.max(1, Math.min(5, Math.trunc(n)));
}

function saveReviewProductSnapshot(productId, snapshot) {
  const pid = Number(productId);
  if (!Number.isFinite(pid) || pid <= 0) return;

  try {
    const raw = localStorage.getItem(REVIEW_PRODUCTS_KEY);
    const prev = raw ? JSON.parse(raw) : null;
    const next = prev && typeof prev === 'object' && !Array.isArray(prev) ? { ...prev } : {};

    next[pid] = {
      ...(typeof snapshot === 'object' && snapshot ? snapshot : {}),
      id: pid,
    };

    localStorage.setItem(REVIEW_PRODUCTS_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

function StarsRow({ order }) {
  const router = useRouter();

  const rateableItems = Array.isArray(order?.items)
    ? order.items.filter((x) => x?.src && !x?.muted)
    : [];

  const handleRate = (value) => {
    const rating = clampRating(value);

    if (order?.statusTitle !== 'Получен') return;

    if (rateableItems.length >= 2) {
      router.push('/profile/reviews');
      return;
    }

    if (rateableItems.length === 1) {
      const item = rateableItems[0];
      const productId =
        Number(item?.id) || Number(order?.reviewProductId) || Number(item?.pid) || 3;

      saveReviewProductSnapshot(productId, {
        name: item?.name || `Товар ${productId}`,
        image: item?.src,
        price: item?.price || '',
      });

      router.push(`/profile/purchased/review/${productId}?rating=${rating}`);
    }
  };

  return (
    <div className={styles.stars} aria-label="Оценка заказа">
      {Array.from({ length: 5 }).map((_, i) => (
        <button
          key={i}
          type="button"
          className={styles.starBtn}
          aria-label={`Поставить оценку ${i + 1} из 5`}
          onClick={(e) => {
            e.stopPropagation();
            handleRate(i + 1);
          }}
        >
          <img src="/icons/product/Star.svg" alt="" aria-hidden="true" className={styles.star} />
        </button>
      ))}
    </div>
  );
}

function OrderCard({ order }) {
  const router = useRouter();
  const thumbs = (order.items ?? []).slice(0, 5);
  const isOpenable =
    order?.statusTitle === 'Оформлен' ||
    order?.statusTitle === 'В пути' ||
    order?.statusTitle === 'Получен' ||
    order?.statusTitle === 'Отменён' ||
    order?.statusTitle === 'В пункте выдачи';

  const detailsHref = (() => {
    const oid = encodeURIComponent(order.id);

    if (order?.statusTitle === 'Получен') return `/profile/orders/received/${oid}`;
    if (order?.statusTitle === 'Отменён') return `/profile/orders/cancelled/${oid}`;
    if (order?.statusTitle === 'Оформлен') return `/profile/orders/in-transit/${oid}`;
    if (order?.statusTitle === 'В пути') return `/profile/orders/in-transit/${oid}`;
    if (order?.statusTitle === 'В пункте выдачи') return `/profile/orders/pickup/${oid}`;

    return `/profile/orders/${oid}`;
  })();

  return (
    <section
      className={styles.card}
      role={isOpenable ? 'button' : undefined}
      tabIndex={isOpenable ? 0 : undefined}
      onClick={() => {
        if (!isOpenable) return;
        router.push(detailsHref);
      }}
      onKeyDown={(e) => {
        if (!isOpenable) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          router.push(detailsHref);
        }
      }}
      aria-label={isOpenable ? 'Открыть заказ' : undefined}
    >
      <StatusHeader title={order.statusTitle} progress={order.progress} />

      {order.subtitle ? <div className={styles.subtitle}>{order.subtitle}</div> : null}

      <div className={styles.thumbsRow}>
        {thumbs.map((x, idx) => (
          <ProductThumb key={`${order.id}_${idx}`} src={x.src} muted={Boolean(x.muted)} />
        ))}
      </div>

      <div className={styles.metaRow}>
        <div className={styles.metaText}>
          {order.itemsCount} {pluralizeRu(order.itemsCount, 'товар', 'товара', 'товаров')}
          <span className={styles.dot}>·</span>
          {formatRub(order.totalRub)}
        </div>
      </div>

      <div className={styles.orderFooter}>
        {order.orderDateTitle ? (
          <span className={styles.orderDate}>{order.orderDateTitle}</span>
        ) : null}
        <span className={styles.orderNumber}>{order.orderNumberShort || order.orderNumber}</span>
      </div>

      {order.showRating ? <StarsRow order={order} /> : null}
    </section>
  );
}

export default function OrdersPage() {
  useEffect(() => {
    // Telegram iOS/Android webview often takes the header title from `document.title`.
    document.title = 'Заказы';
  }, []);

  // The backend Orders module doesn't exist yet (Spec §11) — the RTKQ ghost
  // endpoint returns an empty list. Once the module is ready, just wire
  // `lib/store/api.js#listOrders` to a real fetch — the UI keeps working
  // unchanged.
  const { data: ordersData } = useListOrdersQuery();
  const orders = Array.isArray(ordersData) ? ordersData : [];

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <Header title="Заказы" />
      <main className={styles.main}>
        <Link href="/profile/purchased" className={styles.topLink}>
          <span className={styles.topLinkLeft}>
            <img src="/icons/profile/bag-icon.svg" alt="" className={styles.topLinkIcon} />
            <span className={styles.topLinkText}>Купленные товары</span>
          </span>
          <img src="/icons/global/small-arrow.svg" alt="" className={styles.topLinkChevron} />
        </Link>

        {orders.length > 0 ? (
          <div className={styles.list}>
            {orders.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        ) : (
          <section className={styles.emptyState} role="status" aria-live="polite">
            <div className={styles.emptyTitle}>Заказов пока нет</div>
            <div className={styles.emptyText}>Здесь будут отображаться все ваши заказы</div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
