"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";
import { getMockOrderById } from "../mockOrders";

const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

function formatRub(amount) {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + " ₽";
  } catch {
    return String(amount) + " ₽";
  }
}

function InfoRow({ icon, title, primary, secondary }) {
  return (
    <div className={styles.infoRow}>
      <div className={styles.infoIcon} aria-hidden="true">
        {icon}
      </div>
      <div className={styles.infoText}>
        <div className={styles.infoTitle}>{title}</div>
        <div className={styles.infoPrimary}>{primary}</div>
        {secondary ? (
          <div className={styles.infoSecondary}>{secondary}</div>
        ) : null}
      </div>
      <img src="/icons/global/arrowDownGrey.svg" alt="arrowDown" />
    </div>
  );
}

function ProductRow({ item }) {
  return (
    <div className={styles.productRow}>
      <div className={styles.productThumbWrap} aria-hidden="true">
        <img
          src={item?.src}
          alt=""
          className={
            item?.muted ? styles.productThumbMuted : styles.productThumb
          }
          loading="lazy"
        />
      </div>
      <div className={styles.productMeta}>
        <div className={styles.productName}>{item?.name || "Товар"}</div>
        <div className={styles.productSub}>
          Размер: <span>{item?.size ? `${item.size}` : "—"}</span> &nbsp; ·
          Артикул: <span>{item?.article ? `${item.article}` : ""}</span>
        </div>
        {item?.priceRub ? (
          <div className={styles.productPrice}>{formatRub(item.priceRub)}</div>
        ) : null}
      </div>
    </div>
  );
}

function ActionRow({ label, onClick }) {
  return (
    <button type="button" className={styles.actionRow} onClick={onClick}>
      <span className={styles.actionLabel}>{label}</span>
      <img
        src="/icons/global/small-arrow.svg"
        alt=""
        aria-hidden="true"
        className={styles.actionChevron}
      />
    </button>
  );
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

function BarcodeCard({ code }) {
  if (!code) return null;

  return (
    <section className={styles.barcodeCard} aria-label="Штрихкод для получения">
      <div className={styles.barcodeInner} aria-hidden="true">
        <div className={styles.barcodeLines} />
      </div>
      <div className={styles.barcodeText}>{code}</div>
    </section>
  );
}

function TrackingTimeline() {
  const stages = [
    {
      title: "Оформлен",
      date: "1 апреля",
      events: [{ label: "Добавлен в реестр", date: "3 апреля" }],
    },
    {
      title: "В пути",
      date: "6 апреля",
      events: [
        { label: "Покинул склад в Китае", date: "6 апреля" },
        { label: "Поступил на таможню в Китае", date: "10 апреля" },
        { label: "Поступил на таможню в России", date: "12 апреля" },
      ],
    },
    { title: "В пункте выдачи", date: "", events: [] },
    { title: "Получен", date: "", events: [] },
  ];

  const currentIndex = 1;

  const rows = [];
  stages.forEach((stage, stageIdx) => {
    const canExpand = stageIdx <= currentIndex && stage.events?.length;

    rows.push({
      key: `s_${stageIdx}_${stage.title}`,
      type: "stage",
      stageIdx,
      title: stage.title,
      date: stage.date,
      showCaret: stageIdx <= currentIndex,
      hasNext: stageIdx < stages.length - 1 || canExpand,
      connector:
        stageIdx < currentIndex
          ? "dark"
          : stageIdx === currentIndex && canExpand
            ? "dark"
            : "light",
    });

    if (canExpand) {
      stage.events.forEach((ev, evIdx) => {
        const isLastEvent = evIdx === stage.events.length - 1;
        const hasNext = !(stageIdx === stages.length - 1 && isLastEvent);

        rows.push({
          key: `e_${stageIdx}_${evIdx}_${ev.label}`,
          type: "event",
          stageIdx,
          label: ev.label,
          date: ev.date,
          hasNext,
          connector:
            stageIdx < currentIndex
              ? "dark"
              : stageIdx === currentIndex
                ? isLastEvent
                  ? "light"
                  : "dark"
                : "light",
        });
      });
    }
  });

  return (
    <section className={styles.timelineCard} aria-label="Статус доставки">
      {rows.map((row) => {
        const isStage = row.type === "stage";
        const isUpcoming = row.stageIdx > currentIndex;
        const lineClass =
          row.connector === "dark"
            ? styles.timelineLine
            : styles.timelineLineUpcoming;

        return (
          <div key={row.key} className={styles.timelineRow}>
            <div className={styles.timelineLeft} aria-hidden="true">
              <div
                className={
                  isStage
                    ? isUpcoming
                      ? styles.timelineDotUpcoming
                      : styles.timelineDotDone
                    : styles.timelineDotSmall
                }
              />
              {row.hasNext ? <div className={lineClass} /> : null}
            </div>

            <div className={styles.timelineContent}>
              {isStage ? (
                <div className={styles.timelineHeader}>
                  <div className={styles.timelineTitle}>
                    {row.title}
                    {row.showCaret ? (
                      <img
                        src="/icons/profile/Wrap.svg"
                        aria-hidden="true"
                        alt="icon"
                      />
                    ) : null}
                  </div>
                  {row.date ? (
                    <div className={styles.timelineDate}>{row.date}</div>
                  ) : null}
                </div>
              ) : (
                <div className={styles.timelineEventRow}>
                  <div className={styles.timelineEventLabel}>{row.label}</div>
                  {row.date ? (
                    <div className={styles.timelineEventDate}>{row.date}</div>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </section>
  );
}

function ThumbsStrip({ items }) {
  const [active, setActive] = useState(0);

  if (!Array.isArray(items) || items.length === 0) return null;

  return (
    <div className={styles.thumbsStrip} aria-label="Товары в заказе">
      {items.slice(0, 10).map((it, idx) => {
        const selected = idx === active;
        return (
          <button
            key={it?.id ?? `${idx}`}
            type="button"
            className={
              selected ? styles.thumbPillSelected : styles.thumbPillUnselected
            }
            aria-pressed={selected}
            onClick={() => setActive(idx)}
          >
            <img
              src={it?.src}
              alt=""
              aria-hidden="true"
              className={it?.muted ? styles.thumbImgMuted : styles.thumbImg}
              loading="lazy"
            />
          </button>
        );
      })}
    </div>
  );
}

export default function OrderDetailsClient({ id, variant }) {
  const params = useParams();
  const router = useRouter();
  const resolvedId = id ?? params?.id;

  const order = useMemo(() => getMockOrderById(resolvedId), [resolvedId]);

  useEffect(() => {
    document.title = "Заказ";
  }, []);

  if (!order) {
    return (
      <div className={`tg-viewport ${styles.page}`}>
        <header className={styles.header}>
          <h3 className={styles.title}>Заказ</h3>
        </header>
        <main className={styles.main}>
          <div className={styles.emptyCard} role="status" aria-live="polite">
            Заказ не найден
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const products = Array.isArray(order?.items) ? order.items : [];
  const totals = order?.totals;

  const resolvedVariant = (() => {
    if (variant) return variant;
    if (order?.statusTitle === "Получен") return "received";
    if (order?.statusTitle === "Отменён") return "cancelled";
    if (order?.statusTitle === "В пункте выдачи") return "pickup";
    if (order?.statusTitle === "В пути") return "inTransit";
    return "default";
  })();

  const canShowBarcode =
    resolvedVariant === "pickup" && Boolean(order?.barcode?.code);

  const canShowActions = resolvedVariant !== "cancelled";

  const handleLeaveReview = () => {
    if (resolvedVariant !== "received") return;

    const rateableItems = products.filter((x) => x?.src && !x?.muted);
    if (rateableItems.length >= 2) {
      router.push("/profile/reviews");
      return;
    }

    const single = rateableItems[0];
    const productId = Number(single?.id) || 3;

    saveReviewProductSnapshot(productId, {
      name: single?.name || `Товар ${productId}`,
      image: single?.src,
      price: single?.priceRub ? formatRub(single.priceRub) : "",
    });

    router.push(`/profile/purchased/review/${productId}`);
  };

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <header className={styles.header}>
        <div className={styles.headerFixed}>
          <h3 className={styles.title}>{order.orderDateTitle || "Заказ"}</h3>
          {order.orderNumberShort ? (
            <div className={styles.orderNo}>{order.orderNumberShort}</div>
          ) : null}
        </div>

        <ThumbsStrip items={products} />
      </header>

      <main className={styles.main}>
        <section className={styles.statusBlock}>
          <div className={styles.statusTitle}>{order.statusTitle}</div>
          {order.receivedAt ? (
            <div className={styles.statusDate}>{order.receivedAt}</div>
          ) : null}
          {order.statusSubtitle || order.subtitle ? (
            <div className={styles.statusSubtitle}>
              {order.statusSubtitle || order.subtitle}
            </div>
          ) : null}
          {order.statusHint ? (
            <div className={styles.statusHint}>{order.statusHint}</div>
          ) : null}
        </section>

        {resolvedVariant === "inTransit" ? <TrackingTimeline /> : null}

        {canShowBarcode ? <BarcodeCard code={order.barcode.code} /> : null}

        <section className={styles.infoCard}>
          <InfoRow
            icon={<img src="/icons/profile/location.svg" alt="Location Icon" />}
            title={order?.pickupPoint?.title || "Пункт выдачи"}
            primary={order?.pickupPoint?.address || "—"}
            secondary={order?.pickupPoint?.meta || ""}
          />

          <div className={styles.divider} />

          <InfoRow
            icon={
              <img src="/icons/profile/personIcon.svg" alt="personIcon Icon" />
            }
            title={order?.recipient?.title || "Получатель"}
            primary={order?.recipient?.name || "—"}
            secondary={order?.recipient?.meta || ""}
          />
        </section>

        <section className={styles.productsList} aria-label="Товары">
          {products.map((p, idx) => (
            <ProductRow key={p?.id ?? `${idx}`} item={p} />
          ))}
        </section>

        {totals ? (
          <section className={styles.totalsCard}>
            <div className={styles.totalRowTop}>
              <div className={styles.totalLabel}>{totals.itemsLabel}</div>
              <div className={styles.totalValue}>
                {formatRub(totals.totalRub)}
              </div>
            </div>

            <div className={styles.totalRow}>
              <div className={styles.totalLabelMuted}>Скидка</div>
              <div className={styles.totalValueMuted}>
                {formatRub(totals.discountRub)}
              </div>
            </div>

            {totals.promocode ? (
              <div className={styles.totalSubRow}>
                <div className={styles.totalSubLeft}>
                  <span className={styles.bullet}>•</span>
                  <span>Промокод {totals.promocode.code}</span>
                </div>
                <div className={styles.totalSubRight}>
                  {formatRub(totals.promocode.rub)}
                </div>
              </div>
            ) : null}

            <div className={styles.totalSubRow}>
              <div className={styles.totalSubLeft}>
                <span className={styles.bullet}>•</span>
                <span>Подарочные баллы</span>
              </div>
              <div className={styles.totalSubRight}>
                {formatRub(totals.giftPointsRub)}
              </div>
            </div>

            <div className={styles.totalRow}>
              <div className={styles.totalLabelMuted}>Доставка</div>
              <div className={styles.totalValueMuted}>
                {formatRub(totals.shippingRub)}
              </div>
            </div>

            <div className={styles.totalSubRow}>
              <div className={styles.totalSubLeft}>
                <span className={styles.bullet}>•</span>
                <span>{totals.shippingFrom}</span>
              </div>
              <div className={styles.totalSubRight}>
                {formatRub(totals.shippingRub)}
              </div>
            </div>

            <div className={styles.totalDivider} />

            <div className={styles.totalRowBottom}>
              <div className={styles.totalFinalLabel}>Итого</div>
              <div className={styles.totalFinalValue}>
                {formatRub(totals.finalRub)}
              </div>
            </div>
          </section>
        ) : null}

        {canShowActions ? (
          <section className={styles.actionsCard}>
            {resolvedVariant === "received" ? (
              <>
                <ActionRow label="Оставить отзыв" onClick={handleLeaveReview} />
                <div className={styles.actionsDivider} />
                <ActionRow label="Условия возврата" />
              </>
            ) : (
              <>
                <ActionRow label="Доставка и отслеживание" />
                <div className={styles.actionsDivider} />
                <ActionRow label="Условия возврата" />
              </>
            )}
          </section>
        ) : null}

        <button type="button" className={styles.supportBtn}>
          {resolvedVariant === "cancelled"
            ? "Написать в поддержку"
            : "Чат с поддержкой"}
        </button>
      </main>

      <Footer />
    </div>
  );
}
