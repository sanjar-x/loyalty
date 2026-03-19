"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";
import { mockOrders } from "./mockOrders";

function formatRub(amount) {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + "₽";
  } catch {
    return String(amount) + "₽";
  }
}

function pluralizeRu(n, one, few, many) {
  const x = Math.abs(Number(n)) % 100;
  const x1 = x % 10;
  if (x > 10 && x < 20) return many;
  if (x1 > 1 && x1 < 5) return few;
  if (x1 === 1) return one;
  return many;
}

function StatusHeader({ title, progress, orderNumber }) {
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

function ProductThumb({ src, muted = false }) {
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
    const next =
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

function StarsRow({ order }) {
  const router = useRouter();

  const rateableItems = Array.isArray(order?.items)
    ? order.items.filter((x) => x?.src && !x?.muted)
    : [];

  const handleRate = (value) => {
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

function OrderCard({ order }) {
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
          <span className={styles.dot}>·</span>
          {formatRub(order.totalRub)}
        </div>
      </div>

      {order.showRating ? <StarsRow order={order} /> : null}
    </section>
  );
}

export default function OrdersClient() {
  useEffect(() => {
    // Telegram iOS/Android webview ko'pincha header title'ni `document.title`dan oladi.
    document.title = "Заказы";
  }, []);

  const orders = useMemo(() => mockOrders, []);

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
          {orders.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}
