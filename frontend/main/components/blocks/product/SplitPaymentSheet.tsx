"use client";

import { useMemo, useState, ReactNode } from "react";
import Image from "next/image";

import BottomSheet from "@/components/ui/BottomSheet";
import Button from "@/components/ui/Button";

import styles from "./SplitPaymentSheet.module.css";

interface SplitPaymentData {
  amount?: string | number;
  count?: number;
  text?: string;
}

interface Term {
  id: string;
  title: string;
  sub: string;
  count: number;
  months: number;
}

function toNumber(value: unknown): number {
  const digits = String(value ?? "").replace(/[^0-9]/g, "");
  const n = Number(digits);
  return Number.isFinite(n) ? n : 0;
}

function formatRub(value: number): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n.toLocaleString("ru-RU")} \u20bd`;
}

function formatRubCompact(value: number): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n.toLocaleString("ru-RU")}\u20bd`;
}

function calcInstallment(total: number, count: number): number {
  const t = Number(total);
  const c = Number(count);
  if (!Number.isFinite(t) || t <= 0) return 0;
  if (!Number.isFinite(c) || c <= 0) return 0;
  return Math.round(t / c);
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function formatRuShortDate(date: Date): string {
  // Example: "28 апр." / "12 мая"
  return date
    .toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
    })
    .replace(" \u0433.", "")
    .trim();
}

interface SplitPaymentSheetProps {
  open: boolean;
  onClose: () => void;
  price?: string;
  splitPayment?: SplitPaymentData;
}

export default function SplitPaymentSheet({
  open,
  onClose,
  price,
  splitPayment,
}: SplitPaymentSheetProps) {
  const total = toNumber(price);
  const fallbackAmount = toNumber(splitPayment?.amount);

  const terms = useMemo<Term[]>(() => {
    return [
      {
        id: "2m",
        title: "2 \u043c\u0435\u0441\u044f\u0446\u0430",
        sub: splitPayment?.text || "\u0411\u0435\u0437 \u043f\u0435\u0440\u0435\u043f\u043b\u0430\u0442\u044b",
        count: 2,
        months: 2,
      },
      {
        id: "4m",
        title: "4 \u043c\u0435\u0441\u044f\u0446\u0430",
        sub: "\u041f\u0435\u0440\u0435\u043f\u043b\u0430\u0442\u0430 \u0437\u0430\u0432\u0438\u0441\u0438\u0442 \u043e\u0442 \u0431\u0430\u043d\u043a\u0430",
        count: 4,
        months: 4,
      },
      {
        id: "6m",
        title: "6 \u043c\u0435\u0441\u044f\u0446\u0435\u0432",
        sub: "\u041f\u0435\u0440\u0435\u043f\u043b\u0430\u0442\u0430 \u0437\u0430\u0432\u0438\u0441\u0438\u0442 \u043e\u0442 \u0431\u0430\u043d\u043a\u0430",
        count: 6,
        months: 6,
      },
    ];
  }, [splitPayment?.text]);

  const [selectedId, setSelectedId] = useState<string>("2m");

  const header: ReactNode = (
    <div className={styles.header}>
      <div className={styles.headerTop}>
        <h2 className={styles.title}>\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0440\u043e\u043a</h2>
        <button
          type="button"
          className={styles.closeBtn}
          aria-label="\u0417\u0430\u043a\u0440\u044b\u0442\u044c"
          onClick={onClose}
        >
          <span className={styles.closeIcon} aria-hidden="true">
            <img src="/icons/global/markXBlack.svg" alt="markX" />
          </span>
        </button>
      </div>

      <div className={styles.headerRow}>
        <button
          type="button"
          className={styles.backBtn}
          aria-label="\u041d\u0430\u0437\u0430\u0434"
          onClick={onClose}
        >
          <Image src="/icons/global/split.svg" alt="" width={18} height={18} />
        </button>
        <div className={styles.price}>{formatRub(total)}</div>
      </div>
    </div>
  );

  const selectedTerm = terms.find((t) => t.id === selectedId) || terms[0];

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      ariaLabel="\u0412\u044b\u0431\u043e\u0440 \u0441\u0440\u043e\u043a\u0430 \u0441\u043f\u043b\u0438\u0442\u0430"
      header={header}
      footer={<button className={styles.cta}>\u041a \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u044e</button>}
    >
      <div className={styles.body}>
        <div className={styles.group} role="radiogroup" aria-label="\u0421\u0440\u043e\u043a">
          {terms.map((t) => {
            const active = t.id === selectedId;
            const count = t.count ?? 4;
            const months = t.months ?? 2;
            const intervalDays = Math.max(
              7,
              Math.round((months * 30) / Math.max(1, count - 1)),
            );
            const progressPercent = Math.min(
              100,
              Math.max(0, (1 / count) * 100),
            );
            const installment = calcInstallment(total, count) || fallbackAmount;
            const progressWidth = `${progressPercent}%`;
            const howMany = t.months;
            const filledCount = Math.round((progressPercent / 100) * howMany);

            return (
              <button
                key={t.id}
                type="button"
                role="radio"
                aria-checked={active}
                className={`${styles.option} ${active ? styles.optionActive : ""}`}
                onClick={() => setSelectedId(t.id)}
              >
                <div className={styles.optionTop}>
                  <div className={styles.optionTitle}>{t.title}</div>

                  <div className={styles.optionRight}>
                    <div className={styles.payments}>
                      {count}\u00d7{formatRubCompact(installment)}
                    </div>
                    <div className={styles.sub}>{t.sub}</div>
                  </div>
                </div>

                {active ? (
                  <div className={styles.schedule} aria-label="\u0413\u0440\u0430\u0444\u0438\u043a \u043f\u043b\u0430\u0442\u0435\u0436\u0435\u0439">
                    <div
                      className={styles.scheduleGrid}
                      style={{
                        gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))`,
                      }}
                    >
                      {Array.from({ length: count }).map((_, idx) => (
                        <div key={idx} className={styles.scheduleItem}>
                          <div className={styles.scheduleDate}>
                            {idx === 0
                              ? "\u0421\u0435\u0433\u043e\u0434\u043d\u044f"
                              : formatRuShortDate(
                                  addDays(new Date(), idx * intervalDays),
                                )}
                          </div>
                          <div className={styles.scheduleAmount}>
                            {formatRubCompact(installment) || "\u2014"}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className={styles.progress} aria-hidden="true">
                      {/* <span
                        className={styles.progressFill}
                        style={{ width: progressWidth }}
                      /> */}
                      {Array.from({ length: howMany }).map((_, index) => (
                        <span
                          key={index}
                          className={
                            index < filledCount
                              ? styles.progressFill
                              : styles.progressNotFill
                          }
                          style={{ width: progressWidth }}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
              </button>
            );
          })}
        </div>

        <div className={styles.hint}>
          \u0412\u044b\u0431\u0440\u0430\u043d\u043e:{" "}
          <span className={styles.hintStrong}>{selectedTerm.title}</span>
        </div>
      </div>
    </BottomSheet>
  );
}
