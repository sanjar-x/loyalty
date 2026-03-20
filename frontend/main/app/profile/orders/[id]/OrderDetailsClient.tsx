"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";

const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

interface OrderItem {
  id?: number;
  src?: string;
  name?: string;
  size?: string;
  article?: string;
  priceRub?: number;
  muted?: boolean;
}

interface OrderTotals {
  itemsLabel: string;
  totalRub: number;
  discountRub: number;
  promocode: { code: string; rub: number } | null;
  giftPointsRub: number;
  shippingRub: number;
  shippingFrom: string;
  finalRub: number;
}

interface OrderData {
  id: string;
  statusTitle: string;
  orderDateTitle?: string;
  orderNumberShort?: string;
  statusSubtitle?: string;
  subtitle?: string;
  statusHint?: string;
  receivedAt?: string;
  barcode?: { code: string };
  pickupPoint?: { title: string; address: string; meta: string };
  recipient?: { title: string; name: string; meta: string };
  items: OrderItem[];
  totals?: OrderTotals;
}

type OrderVariant = "received" | "cancelled" | "pickup" | "inTransit" | "default";

function formatRub(amount: number): string {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + " \u20BD";
  } catch {
    return String(amount) + " \u20BD";
  }
}

interface InfoRowProps {
  icon: React.ReactNode;
  title: string;
  primary: string;
  secondary?: string;
}

function InfoRow({ icon, title, primary, secondary }: InfoRowProps) {
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

interface ProductRowProps {
  item: OrderItem;
}

function ProductRow({ item }: ProductRowProps) {
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
          Размер: <span>{item?.size ? `${item.size}` : "\u2014"}</span> &nbsp; &middot;
          Артикул: <span>{item?.article ? `${item.article}` : ""}</span>
        </div>
        {item?.priceRub ? (
          <div className={styles.productPrice}>{formatRub(item.priceRub)}</div>
        ) : null}
      </div>
    </div>
  );
}

interface ActionRowProps {
  label: string;
  onClick?: () => void;
}

function ActionRow({ label, onClick }: ActionRowProps) {
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

interface BarcodeCardProps {
  code: string | undefined;
}

function BarcodeCard({ code }: BarcodeCardProps) {
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
    { title: "В пункте выдачи", date: "", events: [] as { label: string; date: string }[] },
    { title: "Получен", date: "", events: [] as { label: string; date: string }[] },
  ];

  const currentIndex = 1;

  interface TimelineRow {
    key: string;
    type: "stage" | "event";
    stageIdx: number;
    title?: string;
    label?: string;
    date?: string;
    showCaret?: boolean;
    hasNext: boolean;
    connector: "dark" | "light";
  }

  const rows: TimelineRow[] = [];
  stages.forEach((stage, stageIdx) => {
    const canExpand = stageIdx <= currentIndex && stage.events?.length;

    rows.push({
      key: `s_${stageIdx}_${stage.title}`,
      type: "stage",
      stageIdx,
      title: stage.title,
      date: stage.date,
      showCaret: stageIdx <= currentIndex,
      hasNext: stageIdx < stages.length - 1 || !!canExpand,
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

interface ThumbsStripProps {
  items: OrderItem[];
}

function ThumbsStrip({ items }: ThumbsStripProps) {
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

interface OrderDetailsClientProps {
  id?: string;
  variant?: OrderVariant;
}

export default function OrderDetailsClient({ id, variant }: OrderDetailsClientProps) {
  const params = useParams();
  const router = useRouter();
  const resolvedId = id ?? (params?.id as string | undefined);

  // Previously used getMockOrderById - now returns null (no mock data)
  const order: OrderData | null = null;

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
            Нет данных
          </div>
        </main>
        <Footer />
      </div>
    );
  }
}
