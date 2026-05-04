"use client";

import { useEffect, useMemo } from "react";

import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import styles from "./page.module.css";

const RETURN_REQUESTS_KEY = "lm:returnRequests";

function formatRub(amount) {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + " ₽";
  } catch {
    return String(amount) + " ₽";
  }
}

function getRequestFromStorage(id) {
  if (!id) return null;

  try {
    const raw = localStorage.getItem(RETURN_REQUESTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return null;
    return parsed.find((r) => String(r.id) === String(id)) ?? null;
  } catch {
    return null;
  }
}

function normalizeRequest(stored) {
  if (!stored || typeof stored !== "object") return null;

  return {
    ...stored,
    product:
      stored.product && typeof stored.product === "object"
        ? stored.product
        : null,
    photos:
      stored.photos && typeof stored.photos === "object"
        ? stored.photos
        : { product: null, package: null, tag: null },
  };
}

function PhotoThumb({ url }) {
  const resolvedUrl =
    typeof url === "string" ? url : typeof url === "object" ? url?.url : null;
  if (!resolvedUrl) return null;
  return (
    <div className={styles.photoThumb}>
      <img src={resolvedUrl} alt="" className={styles.photoImg} />
    </div>
  );
}

export default function ReturnRequestClient({ id }) {
  // Backend Returns moduli yo'q — yagona manba `localStorage`'da saqlangan
  // foydalanuvchining oldingi yuborgan zayavkasi. Topilmasa "topilmadi"
  // empty state ko'rsatamiz.
  const request = useMemo(() => {
    if (typeof window === "undefined") return null;
    return normalizeRequest(getRequestFromStorage(id));
  }, [id]);

  useEffect(() => {
    document.title = "Заявка на возврат";
  }, []);

  if (!request) {
    return (
      <div className={`tg-viewport ${styles.page}`}>
        <Header title="Заявка на возврат" />
        <main className={styles.main}>
          <section className={styles.card} role="status" aria-live="polite">
            <div className={styles.cardTitle}>Заявка не найдена</div>
            <div className={styles.cardText}>
              Возможно, она была удалена или ещё не создана.
            </div>
          </section>
        </main>
        <Footer />
      </div>
    );
  }

  const nextTitle = request.nextTitle ?? "Что дальше";
  const nextText =
    request.nextText ??
    "Мы проверяем вашу заявку на возврат, пожалуйста, ожидайте решения.";
  const product = request.product;

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <Header title={request.title || "Заявка"} />

      <main className={styles.main}>
        <section className={styles.card}>
          {request.statusText ? (
            <div className={styles.pill}>{request.statusText}</div>
          ) : null}
          <div className={styles.cardTitle}>{nextTitle}</div>
          <div className={styles.cardText}>{nextText}</div>
        </section>

        {product ? (
          <section className={styles.card}>
            <div className={styles.sectionTitle}>Детали возврата</div>
            <div className={styles.productRow}>
              <div className={styles.thumb} aria-hidden="true">
                {product.src ? (
                  <img
                    src={product.src}
                    alt=""
                    className={styles.thumbImg}
                    loading="lazy"
                  />
                ) : null}
              </div>
              <div className={styles.productMeta}>
                <div className={styles.productName}>{product.name || "—"}</div>
                <div className={styles.productSub}>
                  Размер: <span>{product.size || "—"}</span> &nbsp; · Артикул:{" "}
                  <span>{product.article || "—"}</span>
                </div>
                {product.priceRub ? (
                  <div className={styles.productPrice}>
                    {formatRub(product.priceRub)}
                  </div>
                ) : null}
              </div>
            </div>
          </section>
        ) : null}

        <section className={styles.card}>
          <div className={styles.sectionTitle}>Заявка</div>

          <div className={styles.fieldBlock}>
            <div className={styles.fieldLabel}>Причина</div>
            <div className={styles.fieldValue}>
              {request.reasonLabel || "—"}
            </div>
          </div>

          <div className={styles.fieldBlock}>
            <div className={styles.fieldLabel}>Комментарий</div>
            <div className={styles.fieldValue}>{request.comment || "—"}</div>
          </div>

          <div className={styles.fieldBlock}>
            <div className={styles.fieldLabel}>Фото для подтверждения</div>
            <div className={styles.photoRow}>
              <PhotoThumb url={request.photos?.product} />
              <PhotoThumb url={request.photos?.package} />
              <PhotoThumb url={request.photos?.tag} />
            </div>
          </div>
          <button type="button" className={styles.supportBtn}>
            Чат с поддержкой
          </button>
        </section>
      </main>

      <Footer />
    </div>
  );
}
