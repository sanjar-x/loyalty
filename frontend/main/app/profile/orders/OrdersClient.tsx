"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";

interface OrderItem {
  id?: number;
  src: string;
  name?: string;
  size?: string;
  article?: string;
  priceRub?: number;
  price?: string;
  muted?: boolean;
  pid?: number;
}

interface Order {
  id: string;
  statusTitle: string;
  progress?: string;
  orderNumber: string;
  orderDateTitle?: string;
  orderNumberShort?: string;
  statusSubtitle?: string;
  subtitle?: string;
  statusHint?: string;
  itemsCount: number;
  totalRub: number;
  receivedAt?: string;
  showRating?: boolean;
  reviewProductId?: number;
  items: OrderItem[];
  barcode?: { code: string };
  pickupPoint?: { title: string; address: string; meta: string };
  recipient?: { title: string; name: string; meta: string };
  totals?: {
    itemsLabel: string;
    totalRub: number;
    discountRub: number;
    promocode: { code: string; rub: number } | null;
    giftPointsRub: number;
    shippingRub: number;
    shippingFrom: string;
    finalRub: number;
  };
}

function formatRub(amount: number): string {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + "\u20BD";
  } catch {
    return String(amount) + "\u20BD";
  }
}

function pluralizeRu(n: number, one: string, few: string, many: string): string {
  const x = Math.abs(Number(n)) % 100;
  const x1 = x % 10;
  if (x > 10 && x < 20) return many;
  if (x1 > 1 && x1 < 5) return few;
  if (x1 === 1) return one;
  return many;
}

interface StatusHeaderProps {
  title: string;
  progress?: string;
  orderNumber: string;
}

function StatusHeader({ title, progress, orderNumber }: StatusHeaderProps) {
  return (
    <div className={`${styles.statusRow}`}>
      <div className={styles.statusLeft}>
        <div
          className={`${styles.statusTitle} ${title == "Отменён" ? `${styles.makeGrey}` : ""} ${title == "Получен" ? `${styles.makeGrey}` : ""}`}
        >
          {title}
          <img
            src="/icons/global/small-arrow.svg"
            alt=""
            className={styles.chevron}
          />
        </div>
        {progress ? (
          <div
            className={`${styles.statusProgress} ${title == "Отменён" ? `${styles.makeGrey}` : ""} ${title == "Получен" ? `${styles.makeGrey}` : ""}`}
          >
            {progress}
          </div>
        ) : null}
      </div>
      <div className={styles.orderNumber}>{orderNumber}</div>
    </div>
  );
}

interface ProductThumbProps {
  src: string;
  muted?: boolean;
}

function ProductThumb({ src, muted = false }: ProductThumbProps) {
  return (
    <div className={styles.thumbWrap}>
      <img
        src={src}
        alt=""
        className={muted ? styles.thumbMuted : styles.thumb}
        loading="lazy"
      />
    </div>
  );
}

const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

function clampRating(value: unknown): number {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return 0;
  return Math.max(1, Math.min(5, Math.trunc(n)));
}

function saveReviewProductSnapshot(productId: number, snapshot: Record<string, unknown>): void {
  const pid = Number(productId);
  if (!Number.isFinite(pid) || pid <= 0) return;

  try {
    const raw = localStorage.getItem(REVIEW_PRODUCTS_KEY);
    const prev = raw ? JSON.parse(raw) : null;
    const next: Record<string, unknown> =
      prev && typeof prev === "object" && !Array.isArray(prev)
        ? { ...prev }
        : {};

    next[pid] = {
      ...(typeof snapshot === "object" && snapshot ? snapshot : {}),
      id: pid,
    };

    localStorage.setItem(REVIEW_PRODUCTS_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

interface StarsRowProps {
  order: Order;
}

function StarsRow({ order }: StarsRowProps) {
  const router = useRouter();

  const rateableItems = Array.isArray(order?.items)
    ? order.items.filter((x) => x?.src && !x?.muted)
    : [];

  const handleRate = (value: number) => {
    const rating = clampRating(value);

    if (order?.statusTitle !== "Получен") return;

    if (rateableItems.length >= 2) {
      router.push("/profile/reviews");
      return;
    }

    if (rateableItems.length === 1) {
      const item = rateableItems[0];
      const productId =
        Number(item?.id) ||
        Number(order?.reviewProductId) ||
        Number(item?.pid) ||
        3;

      saveReviewProductSnapshot(productId, {
        name: item?.name || `Товар ${productId}`,
        image: item?.src,
        price: item?.price || "",
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
          <img
            src="/icons/product/Star.svg"
            alt=""
            aria-hidden="true"
            className={styles.star}
          />
        </button>
      ))}
    </div>
  );
}

interface OrderCardProps {
  order: Order;
}

function OrderCard({ order }: OrderCardProps) {
  const router = useRouter();
  const thumbs = (order.items ?? []).slice(0, 5);
  const isOpenable =
    order?.statusTitle === "Оформлен" ||
    order?.statusTitle === "В пути" ||
    order?.statusTitle === "Получен" ||
    order?.statusTitle === "Отменён" ||
    order?.statusTitle === "В пункте выдачи";

  const detailsHref = (() => {
    const oid = encodeURIComponent(order.id);

    if (order?.statusTitle === "Получен")
      return `/profile/orders/received/${oid}`;
    if (order?.statusTitle === "Отменён")
      return `/profile/orders/cancelled/${oid}`;
    if (order?.statusTitle === "Оформлен")
      return `/profile/orders/in-transit/${oid}`;
    if (order?.statusTitle === "В пути")
      return `/profile/orders/in-transit/${oid}`;
    if (order?.statusTitle === "В пункте выдачи")
      return `/profile/orders/pickup/${oid}`;

    return `/profile/orders/${oid}`;
  })();

  return (
    <section
      className={styles.card}
      role={isOpenable ? "button" : undefined}
      tabIndex={isOpenable ? 0 : undefined}
      onClick={() => {
        if (!isOpenable) return;
        router.push(detailsHref);
      }}
      onKeyDown={(e) => {
        if (!isOpenable) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          router.push(detailsHref);
        }
      }}
      aria-label={isOpenable ? "Открыть заказ" : undefined}
    >
      <StatusHeader
        title={order.statusTitle}
        progress={order.progress}
        orderNumber={order.orderNumber}
      />

      {order.subtitle ? (
        <div className={styles.subtitle}>{order.subtitle}</div>
      ) : null}

      <div className={styles.thumbsRow}>
        {thumbs.map((x, idx) => (
          <ProductThumb
            key={`${order.id}_${idx}`}
            src={x.src}
            muted={Boolean(x.muted)}
          />
        ))}
      </div>

      <div className={styles.metaRow}>
        <div className={styles.metaText}>
          {order.itemsCount}{" "}
          {pluralizeRu(order.itemsCount, "товар", "товара", "товаров")}
          <span className={styles.dot}>&middot;</span>
          {formatRub(order.totalRub)}
        </div>
      </div>

      {order.showRating ? <StarsRow order={order} /> : null}
    </section>
  );
}

export default function OrdersClient() {
  useEffect(() => {
    document.title = "Заказы";
  }, []);

  const orders = useMemo<Order[]>(() => [], []);

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <h3 className={styles.ordersClientstitle}>Заказы</h3>
      <main className={styles.main}>
        <Link href="/profile/purchased" className={styles.topLink}>
          <span className={styles.topLinkLeft}>
            <img
              src="/icons/profile/bag-icon.svg"
              alt=""
              className={styles.topLinkIcon}
            />
            <span className={styles.topLinkText}>Купленные товары</span>
          </span>
          <img
            src="/icons/global/small-arrow.svg"
            alt=""
            className={styles.topLinkChevron}
          />
        </Link>

        <div className={styles.list}>
          {orders.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#999" }}>
              Нет данных
            </div>
          ) : (
            orders.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
