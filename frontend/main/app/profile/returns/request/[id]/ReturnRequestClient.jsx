"use client";

import { useEffect, useMemo } from "react";

import Footer from "@/components/layout/Footer";
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

function makeFallbackRequest(id) {
  return {
    id: id ?? "demo",
    title: "Заявка",
    no: "—",
    statusText: "На рассмотрении",
    statusType: "review",
    nextTitle: "Что дальше",
    nextText:
      "Мы проверяем вашу заявку на возврат, пожалуйста, ожидайте решения.",
    product: {
      orderNo: "Заказ №4523464267",
      src: "/products/shoes-2.png",
      name: "Джинсы Carne Bollente",
      size: "L",
      article: "4465457",
      priceRub: 9119,
    },
    reasonLabel: "—",
    comment: "—",
    photos: {
      product: null,
      package: null,
      tag: null,
    },
  };
}

function normalizeRequest(stored, id) {
  const fallback = makeFallbackRequest(id);
  if (!stored || typeof stored !== "object") return fallback;

  return {
    ...fallback,
    ...stored,
    product: {
      ...fallback.product,
      ...(stored.product && typeof stored.product === "object"
        ? stored.product
        : {}),
    },
    photos: {
      ...fallback.photos,
      ...(stored.photos && typeof stored.photos === "object"
        ? stored.photos
        : {}),
    },
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
  const request = useMemo(() => {
    if (typeof window === "undefined") return makeFallbackRequest(id);
    const fromStorage = getRequestFromStorage(id);
    return normalizeRequest(fromStorage, id);
  }, [id]);

  useEffect(() => {
    document.title = "Заявка на возврат";
  }, []);

  const nextTitle = request?.nextTitle ?? "Что дальше";
  const nextText =
    request?.nextText ??
    "Мы проверяем вашу заявку на возврат, пожалуйста, ожидайте решения.";

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <header className={styles.header}>
        <div className={styles.headerCenter}>
          <div className={styles.headerTitle}>{request.title}</div>
          <div className={styles.headerNo}>№{request.no}</div>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.card}>
          <div className={styles.pill}>{request.statusText}</div>
          <div className={styles.cardTitle}>{nextTitle}</div>
          <div className={styles.cardText}>{nextText}</div>
        </section>

        <section className={styles.card}>
          <div className={styles.sectionTitle}>Детали возврата</div>
          <div className={styles.productRow}>
            <div className={styles.thumb} aria-hidden="true">
              <img
                src={request.product.src}
                alt=""
                className={styles.thumbImg}
                loading="lazy"
              />
            </div>
            <div className={styles.productMeta}>
              <div className={styles.productName}>{request.product.name}</div>
              <div className={styles.productSub}>
                Размер: <span>{request.product.size}</span> &nbsp; · Артикул:{" "}
                <span>{request.product.article}</span>
              </div>
              <div className={styles.productPrice}>
                {formatRub(request.product.priceRub)}
              </div>
            </div>
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.sectionTitle}>Заявка</div>

          <div className={styles.fieldBlock}>
            <div className={styles.fieldLabel}>Причина</div>
            <div className={styles.fieldValue}>{request.reasonLabel}</div>
          </div>

          <div className={styles.fieldBlock}>
            <div className={styles.fieldLabel}>Комментарий</div>
            <div className={styles.fieldValue}>{request.comment}</div>
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
