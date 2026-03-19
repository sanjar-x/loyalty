"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

const RETURN_DRAFT_KEY = "lm:returnDraft";
const RETURN_REQUESTS_KEY = "lm:returnRequests";

function formatRub(amount) {
  try {
    return new Intl.NumberFormat("ru-RU").format(amount) + " ₽";
  } catch {
    return String(amount) + " ₽";
  }
}

function getDraft() {
  try {
    const raw = localStorage.getItem(RETURN_DRAFT_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    return null;
  }
}

function Radio({ checked }) {
  return (
    <div
      className={checked ? styles.radioChecked : styles.radio}
      aria-hidden="true"
    >
      {checked ? (
        <img
          src="/icons/profile/CheckMark.svg"
          alt=""
          className={styles.radioTick}
        />
      ) : null}
    </div>
  );
}

export default function CreateReturnClient() {
  const router = useRouter();

  const fileInputRef = useRef(null);
  const commentRef = useRef(null);
  const activeSlotRef = useRef(null);

  const [selected, setSelected] = useState("size");
  const [step, setStep] = useState("reason");
  const [comment, setComment] = useState("");
  const [photos, setPhotos] = useState({
    product: null,
    package: null,
    tag: null,
  });

  useEffect(() => {
    document.title = "Оформление возврата";
  }, []);

  const draft = useMemo(() => getDraft(), []);

  const product = draft?.product ?? {
    orderNo: "Заказ №4523464267",
    src: "/products/shoes-2.png",
    name: "Джинсы Carne Bollente",
    size: "L",
    article: "4465457",
    priceRub: 9119,
  };

  const reasons = [
    { id: "wrong", label: "Не тот товар" },
    { id: "size", label: "Не тот размер" },
    { id: "defect", label: "Товар с браком" },
  ];

  const selectedReasonLabel =
    reasons.find((reason) => reason.id === selected)?.label ?? "";

  const photoSlots = [
    { id: "product", label: "Товар" },
    { id: "package", label: "Упаковка" },
    { id: "tag", label: "Бирка" },
  ];

  function handlePickPhotos(slotId) {
    activeSlotRef.current = slotId;
    fileInputRef.current?.click();
  }

  function handleFilesPicked(event) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;

    setPhotos((prev) => {
      const nextState = { ...prev };
      const order = photoSlots.map((s) => s.id);
      const active = activeSlotRef.current;
      const startIndex = active ? Math.max(0, order.indexOf(active)) : 0;

      const slotsToFill = [
        ...order.slice(startIndex),
        ...order.slice(0, startIndex),
      ].filter((slotId, idx, arr) => arr.indexOf(slotId) === idx);

      let fileIndex = 0;
      for (const slotId of slotsToFill) {
        if (fileIndex >= files.length) break;

        // If user selected 1 file for a specific slot, we overwrite that slot.
        // If multiple files are selected, we fill in order (overwriting the active slot, then empty ones).
        const shouldWrite =
          slotId === active || nextState[slotId] == null || files.length > 1;
        if (!shouldWrite) continue;

        const file = files[fileIndex++];
        const prevPhoto = nextState[slotId];
        if (prevPhoto?.url) {
          try {
            URL.revokeObjectURL(prevPhoto.url);
          } catch {
            // ignore
          }
        }

        nextState[slotId] = {
          id: `${slotId}-${file.name}-${file.size}-${file.lastModified}-${Math.random()}`,
          url: URL.createObjectURL(file),
          file,
        };
      }

      return nextState;
    });

    event.target.value = "";
  }

  function handleRemovePhoto(slotId) {
    setPhotos((prev) => {
      const target = prev[slotId];
      if (target?.url) {
        try {
          URL.revokeObjectURL(target.url);
        } catch {
          // ignore
        }
      }

      return {
        ...prev,
        [slotId]: null,
      };
    });
  }

  function handlePrimaryAction() {
    if (step === "reason") {
      setStep("details");
      return;
    }

    const hasComment = comment.trim().length > 0;
    const hasAllPhotos = photoSlots.every((slot) => Boolean(photos[slot.id]));
    if (!hasComment || !hasAllPhotos) return;

    const now = new Date();
    const months = [
      "января",
      "февраля",
      "марта",
      "апреля",
      "мая",
      "июня",
      "июля",
      "августа",
      "сентября",
      "октября",
      "ноября",
      "декабря",
    ];

    const title = `Заявка от ${now.getDate()} ${months[now.getMonth()]}`;
    const id = `${Date.now()}_${Math.floor(Math.random() * 10000)}`;
    const no = String(Math.floor(1e10 + Math.random() * 9e10));

    const requestPayload = {
      id,
      no,
      title,
      statusText: "На рассмотрении",
      statusType: "review",
      nextTitle: "Что дальше",
      nextText:
        "Мы проверяем вашу заявку на возврат, пожалуйста, ожидайте решения.",
      product,
      reasonId: selected,
      reasonLabel: selectedReasonLabel,
      comment: comment.trim(),
      photos,
      createdAt: now.toISOString(),
    };

    try {
      const raw = localStorage.getItem(RETURN_REQUESTS_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      const prev = Array.isArray(parsed) ? parsed : [];
      localStorage.setItem(
        RETURN_REQUESTS_KEY,
        JSON.stringify([requestPayload, ...prev]),
      );
    } catch {
      // ignore
    }

    router.push(`/profile/returns/request/${id}`);
  }

  const primaryLabel = step === "reason" ? "Продолжить" : "Отправить заявку";
  const isSubmitDisabled =
    step === "details" &&
    (comment.trim().length === 0 ||
      photoSlots.some((slot) => !photos[slot.id]));

  function autosize(textarea) {
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${textarea.scrollHeight}px`;
  }

  return (
    <div className={`tg-viewport ${styles.page}`}>
      <header className={styles.header}>
        <h3 className={styles.title}>Оформление возврата</h3>
      </header>

      <main className={styles.main}>
        <section className={styles.orderCard}>
          <div className={styles.orderNo}>{product.orderNo}</div>
          <div className={styles.productRow}>
            <div className={styles.thumb} aria-hidden="true">
              <img
                src={product.src}
                alt=""
                className={styles.thumbImg}
                loading="lazy"
              />
            </div>
            <div className={styles.productMeta}>
              <div className={styles.productName}>{product.name}</div>
              <div className={styles.productSub}>
                Размер: <span>{product.size}</span> · Артикул:{" "}
                <span>{product.article}</span>
              </div>
              <div className={styles.productPrice}>
                {formatRub(product.priceRub)}
              </div>
            </div>
          </div>
        </section>

        {step === "reason" ? (
          <section className={styles.reasonCard} aria-label="Причина возврата">
            <div className={styles.reasonTitle}>Выберите причину</div>
            <div className={styles.reasonList} role="radiogroup">
              {reasons.map((r) => {
                const isChecked = selected === r.id;
                return (
                  <button
                    key={r.id}
                    type="button"
                    className={styles.reasonRow}
                    role="radio"
                    aria-checked={isChecked}
                    onClick={() => setSelected(r.id)}
                  >
                    <span className={styles.reasonLabel}>{r.label}</span>
                    <Radio checked={isChecked} />
                  </button>
                );
              })}
            </div>
          </section>
        ) : (
          <div className={styles.sectionCards}>
            <section className={styles.sectionCard} aria-label="Причина">
              <div className={styles.sectionTitle}>Причина</div>
              <div className={styles.sectionValue}>{selectedReasonLabel}</div>
            </section>
            <div className={styles.fieldWrapsSection}>
              <div className={styles.sectionTitle}>Комментарий</div>
              <div
                className={styles.fieldWrap}
                data-filled={comment ? "true" : "false"}
                aria-label="Опишите проблему"
              >
                <div className={styles.fieldLabel}>Опишите проблему</div>
                <textarea
                  ref={commentRef}
                  className={styles.fieldInput}
                  aria-label="Опишите проблему"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  onInput={(e) => autosize(e.currentTarget)}
                  rows={1}
                />
                {comment ? (
                  <button
                    type="button"
                    className={styles.clearBtn}
                    aria-label="Очистить комментарий"
                    onClick={() => {
                      setComment("");
                      requestAnimationFrame(() => autosize(commentRef.current));
                    }}
                  >
                    <img
                      src="/icons/global/xicon.svg"
                      alt=""
                      aria-hidden="true"
                      className={styles.clearIcon}
                    />
                  </button>
                ) : null}
              </div>
            </div>
            <div className={styles.photoBlock} aria-label="Фото">
              <div className={styles.sectionTitle}>Фото</div>

              <div className={styles.photosRow}>
                <input
                  ref={fileInputRef}
                  className={styles.fileInput}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFilesPicked}
                />

                {photoSlots.map((slot) => {
                  const photo = photos[slot.id];

                  if (!photo) {
                    return (
                      <button
                        key={slot.id}
                        type="button"
                        className={styles.photoTile}
                        onClick={() => handlePickPhotos(slot.id)}
                      >
                        <img
                          src="/icons/global/uploadImage.svg"
                          alt=""
                          aria-hidden="true"
                          className={styles.photoIcon}
                        />
                        <p className={styles.photoLabel}>{slot.label}</p>
                      </button>
                    );
                  }

                  return (
                    <div key={slot.id} className={styles.photoThumb}>
                      <img src={photo.url} alt="" className={styles.photoImg} />
                      <button
                        type="button"
                        className={styles.removeBtn}
                        aria-label="Удалить фото"
                        onClick={() => handleRemovePhoto(slot.id)}
                      >
                        <img
                          src="/icons/global/closeWhite.svg"
                          alt=""
                          aria-hidden="true"
                          className={styles.removeIcon}
                        />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        <div className={styles.bottomSpacer} />
      </main>

      <div className={styles.bottomBar}>
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={handlePrimaryAction}
          disabled={isSubmitDisabled}
        >
          {primaryLabel}
        </button>
      </div>
    </div>
  );
}
