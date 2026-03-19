"use client";

import { useMemo, useState } from "react";
import Image from "next/image";

import BottomSheet from "@/components/ui/BottomSheet";
import Button from "@/components/ui/Button";

import styles from "./SplitPaymentSheet.module.css";

function toNumber(value) {
  const digits = String(value ?? "").replace(/[^0-9]/g, "");
  const n = Number(digits);
  return Number.isFinite(n) ? n : 0;
}

function formatRub(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n.toLocaleString("ru-RU")} ₽`;
}

function formatRubCompact(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n.toLocaleString("ru-RU")}₽`;
}

function calcInstallment(total, count) {
  const t = Number(total);
  const c = Number(count);
  if (!Number.isFinite(t) || t <= 0) return 0;
  if (!Number.isFinite(c) || c <= 0) return 0;
  return Math.round(t / c);
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function formatRuShortDate(date) {
  // Example: "28 апр." / "12 мая"
  return date
    .toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
    })
    .replace(" г.", "")
    .trim();
}

export default function SplitPaymentSheet({
  open,
  onClose,
  price,
  splitPayment,
}) {
  const total = toNumber(price);
  const fallbackAmount = toNumber(splitPayment?.amount);

  const terms = useMemo(() => {
    // Bu yerda backend kelajakda terms/plans beradigan bo‘lsa, shu logicni almashtirish oson.
    return [
      {
        id: "2m",
        title: "2 месяца",
        sub: splitPayment?.text || "Без переплаты",
        count: 2,
        months: 2,
      },
      {
        id: "4m",
        title: "4 месяца",
        sub: "Переплата зависит от банка",
        count: 4,
        months: 4,
      },
      {
        id: "6m",
        title: "6 месяцев",
        sub: "Переплата зависит от банка",
        count: 6,
        months: 6,
      },
    ];
  }, [splitPayment?.text]);

  const [selectedId, setSelectedId] = useState("2m");

  const header = (
    <div className={styles.header}>
      <div className={styles.headerTop}>
        <h2 className={styles.title}>Выберите срок</h2>
        <button
          type="button"
          className={styles.closeBtn}
          aria-label="Закрыть"
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
          aria-label="Назад"
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
      ariaLabel="Выбор срока сплита"
      header={header}
      footer={<button className={styles.cta}>К оформлению</button>}
    >
      <div className={styles.body}>
        <div className={styles.group} role="radiogroup" aria-label="Срок">
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
                      {count}×{formatRubCompact(installment)}
                    </div>
                    <div className={styles.sub}>{t.sub}</div>
                  </div>
                </div>

                {active ? (
                  <div className={styles.schedule} aria-label="График платежей">
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
                              ? "Сегодня"
                              : formatRuShortDate(
                                  addDays(new Date(), idx * intervalDays),
                                )}
                          </div>
                          <div className={styles.scheduleAmount}>
                            {formatRubCompact(installment) || "—"}
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
          Выбрано:{" "}
          <span className={styles.hintStrong}>{selectedTerm.title}</span>
        </div>
      </div>
    </BottomSheet>
  );
}
