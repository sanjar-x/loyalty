"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import Footer from "@/components/layout/Footer";
import styles from "./page.module.css";

const RETURN_DRAFT_KEY = "lm:returnDraft";
const RETURN_REQUESTS_KEY = "lm:returnRequests";

function saveReturnDraft(payload) {
  try {
    localStorage.setItem(RETURN_DRAFT_KEY, JSON.stringify(payload));
  } catch {
    // ignore
  }
}

function formatRub(amount) {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + " ₽";
  } catch {
    return String(amount) + " ₽";
  }
}

function StatusPill({ type, children }) {
  const className = (() => {
    if (type === "approved") return styles.pillApproved;
    if (type === "review") return styles.pillReview;
    if (type === "rejected") return styles.pillRejected;
    return styles.pillClosed;
  })();

  return <div className={`${styles.statusPill} ${className}`}>{children}</div>;
}

function RequestCard({ req }) {
  const router = useRouter();
  const isClickable = Boolean(req?.id) && !req?.disabled;

  return (
    <section
      className={`${styles.card} ${req.disabled ? styles.cardDisabled : ""}`}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={() => {
        if (!isClickable) return;
        router.push(`/profile/returns/request/${req.id}`);
      }}
      onKeyDown={(e) => {
        if (!isClickable) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          router.push(`/profile/returns/request/${req.id}`);
        }
      }}
    >
      <div className={styles.cardTop}>
        <div className={styles.cardNo}>№{req.no}</div>
        <StatusPill type={req.statusType}>{req.statusText}</StatusPill>
      </div>

      <div className={styles.cardTitle}>{req.title}</div>

      <div className={styles.productRow}>
        <div className={styles.thumb} aria-hidden="true">
          <img src={req.product.src} alt="" className={styles.thumbImg} />
        </div>
        <div className={styles.productMeta}>
          <div className={styles.productName}>{req.product.name}</div>
          <div className={styles.productSub}>
            Размер: <span>{req.product.size}</span> &nbsp;· Артикул:{" "}
            <span>{req.product.article}</span>
          </div>
          <div className={styles.productPrice}>
            {formatRub(req.product.priceRub)}
          </div>
        </div>
      </div>
    </section>
  );
}

function FaqRow({ icon, title, text }) {
  return (
    <div className={styles.faqRow}>
      <div className={styles.faqIcon} aria-hidden="true">
        <img src={`${icon}`} alt="icon" />
      </div>
      <div>
        <div className={styles.faqTitle}>{title}</div>
        <div className={styles.faqText}>{text}</div>
      </div>
    </div>
  );
}

function ReturnOrderCard({ order }) {
  const router = useRouter();

  return (
    <section
      className={`${styles.card} ${styles.returnCard} ${
        order.disabled ? styles.cardDisabled : ""
      }`}
      role="button"
      tabIndex={0}
      onClick={() => {
        const first = order?.items?.[0];
        saveReturnDraft({
          product: {
            orderNo: order.orderNo,
            src: first?.src,
            name: first?.name,
            size: first?.size,
            article: first?.article,
            priceRub: first?.priceRub,
          },
        });
        router.push("/profile/returns/create");
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          const first = order?.items?.[0];
          saveReturnDraft({
            product: {
              orderNo: order.orderNo,
              src: first?.src,
              name: first?.name,
              size: first?.size,
              article: first?.article,
              priceRub: first?.priceRub,
            },
          });
          router.push("/profile/returns/create");
        }
      }}
    >
      <div className={styles.returnTopRow}>
        <div className={styles.returnOrderNo}>{order.orderNo}</div>
        {order.pill ? (
          <div className={styles.returnPill}>{order.pill}</div>
        ) : null}
      </div>

      <div className={styles.returnTitle}>{order.title}</div>

      <div className={styles.returnItems}>
        {order.items.map((it, idx) => (
          <div key={`${it.article}_${idx}`}>
            {idx > 0 ? <div className={styles.returnDivider} /> : null}
            <div className={styles.returnProductRow}>
              <div className={styles.returnThumb} aria-hidden="true">
                <img
                  src={it.src}
                  alt=""
                  className={styles.returnThumbImg}
                  loading="lazy"
                />
              </div>
              <div className={styles.returnProductMeta}>
                <div className={styles.returnProductName}>{it.name}</div>
                <div className={styles.returnProductSub}>
                  Размер: <span>{it.size}</span> · Артикул:{" "}
                  <span>{it.article}</span>
                </div>
                <div className={styles.returnProductPrice}>
                  {formatRub(it.priceRub)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ReturnsPage() {
  const [tab, setTab] = useState("requests");
  const [requests] = useState(() => {
    if (typeof window === "undefined") return [];
    try {
      const raw = localStorage.getItem(RETURN_REQUESTS_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });
  const router = useRouter();

  useEffect(() => {
    document.title = "Возвраты";
  }, []);

  const hasRequests = Array.isArray(requests) && requests.length > 0;

  const returnOrders = useMemo(
    () => [
      {
        orderNo: "Заказ №4523464267",
        title: "Получен 12 марта",
        items: [
          {
            src: "/products/shoes-2.png",
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            priceRub: 9119,
          },
        ],
      },
      {
        orderNo: "Заказ №4523464267",
        title: "Получен 12 марта",
        items: [
          {
            src: "/products/shoes-2.png",
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            priceRub: 9119,
          },
          {
            src: "/products/shoes-2.png",
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            priceRub: 9119,
          },
        ],
      },
      {
        orderNo: "Заказ №4523464267",
        title: "Получен 9 марта",
        pill: "Срок возврата истек",
        disabled: true,
        items: [
          {
            src: "/products/shoes-2.png",
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            priceRub: 9119,
          },
        ],
      },
    ],
    [],
  );

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <header className={styles.header}>
        <h3 className={styles.title}>Возвраты</h3>
        <div className={styles.tabsWrap} role="tablist" aria-label="Разделы">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "requests"}
            className={`${styles.tabBtn} ${
              tab === "requests" ? styles.tabBtnActive : ""
            }`}
            onClick={() => setTab("requests")}
          >
            Заявки
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "return"}
            className={`${styles.tabBtn} ${
              tab === "return" ? styles.tabBtnActive : ""
            }`}
            onClick={() => setTab("return")}
          >
            Вернуть товары
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {tab === "requests" ? (
          hasRequests ? (
            <div className={styles.cards}>
              {requests.map((r, idx) => (
                <RequestCard key={`${r.title}_${idx}`} req={r} />
              ))}
            </div>
          ) : (
            <section className={styles.emptyStateCard}>
              <div className={styles.emptyStateTitle}>Возвратов пока нет</div>
              <div className={styles.emptyStateText}>
                Все оформленные заявки на возврат будут отображаться здесь
              </div>
              <button
                type="button"
                className={styles.emptyStateBtn}
                onClick={() => {
                  saveReturnDraft({
                    product: {
                      orderNo: "Заказ №4523464267",
                      src: "/products/shoes-2.png",
                      name: "Джинсы Carne Bollente",
                      size: "L",
                      article: "4465457",
                      priceRub: 9119,
                    },
                  });
                  router.push("/profile/returns/create");
                }}
              >
                Создать заявку
              </button>
            </section>
          )
        ) : (
          <div className={styles.cards}>
            {returnOrders.map((o, idx) => (
              <ReturnOrderCard key={`${o.title}_${idx}`} order={o} />
            ))}
          </div>
        )}

        {tab === "requests" ? (
          <section className={styles.faq} aria-label="Вопросы и ответы">
            <FaqRow
              icon="/icons/profile/questionIcon.svg"
              title="Можно ли вернуть товар?"
              text="Да, вернуть можно любой товар, если он не попадает в список исключений."
            />
            <FaqRow
              icon="/icons/profile/returnIocn.svg"
              title="Как вернуть товар?"
              text="Перейдите во вкладку «Вернуть товары», выберите нужный заказ и заполните заявку. Затем дождитесь одобрения и отнесите товар в указанный пункт выдачи."
            />
            <FaqRow
              icon="/icons/profile/notAcces.svg"
              title="Что нельзя вернуть?"
              text="На возврат не принимаются товары со следами использования, а также если ошибка в размере была со стороны покупателя."
            />
            <FaqRow
              icon="/icons/profile/clock.svg"
              title="Как долго можно вернуть?"
              text="Товары можно вернуть в течении 3 дней после получения."
            />
            <FaqRow
              icon="/icons/profile/cardIcon.svg"
              title="Когда вернутся деньги?"
              text="Деньги возвращаются в течение 2–3 дней после того, как товар будет проверен на складе."
            />

            <button type="button" className={styles.supportBtn}>
              Чат с поддержкой
            </button>
          </section>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
