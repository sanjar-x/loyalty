"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./page.module.css";

const REVIEW_PRODUCTS_KEY = "lm:reviewProducts";

interface ReviewProduct {
  id?: number;
  name?: string;
  image?: string;
  price?: string;
  [key: string]: unknown;
}

interface PhotoEntry {
  id: string;
  file: File;
  url: string;
}

function clampRating(value: unknown): number {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(5, Math.trunc(n)));
}

interface ReviewClientProps {
  id?: string;
}

export default function ReviewClient({ id }: ReviewClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prosRef = useRef<HTMLTextAreaElement>(null);
  const consRef = useRef<HTMLTextAreaElement>(null);
  const commentRef = useRef<HTMLTextAreaElement>(null);

  const autosize = (el: HTMLTextAreaElement | null) => {
    if (!el) return;
    const BASE = 55;
    el.style.height = "0px";
    const next = Math.max(BASE, el.scrollHeight);
    el.style.height = `${next}px`;
  };

  useEffect(() => {
    document.title = "Оцените товар";
  }, []);

  const pid = useMemo(() => {
    const n = Number(id);
    return Number.isFinite(n) ? n : null;
  }, [id]);

  // No mock data - product comes from localStorage only
  const [product, setProduct] = useState<ReviewProduct | null>(null);

  useEffect(() => {
    if (!pid) return;
    try {
      const raw = localStorage.getItem(REVIEW_PRODUCTS_KEY);
      const saved = raw ? JSON.parse(raw) : null;
      if (saved && typeof saved === "object" && !Array.isArray(saved)) {
        const fromStorage = saved[pid];
        if (fromStorage && typeof fromStorage === "object") {
          setProduct(fromStorage as ReviewProduct);
        }
      }
    } catch {
      // ignore
    }
  }, [pid]);

  const resolvedImage = useMemo(() => {
    return product?.image || "";
  }, [product]);

  const initialRating = clampRating(searchParams?.get("rating"));
  const [rating, setRating] = useState(initialRating);
  const [pros, setPros] = useState("");
  const [cons, setCons] = useState("");
  const [comment, setComment] = useState("");
  const [photos, setPhotos] = useState<PhotoEntry[]>([]);

  useEffect(() => {
    autosize(prosRef.current);
  }, [pros]);

  useEffect(() => {
    autosize(consRef.current);
  }, [cons]);

  useEffect(() => {
    autosize(commentRef.current);
  }, [comment]);

  useEffect(() => {
    return () => {
      photos.forEach((p) => {
        try {
          URL.revokeObjectURL(p.url);
        } catch {
          // ignore
        }
      });
    };
  }, [photos]);

  const addPhotos = (files: FileList | null) => {
    const list = Array.from(files ?? []).filter((f) => f instanceof File);
    if (!list.length) return;

    setPhotos((prev) => [
      ...prev,
      ...list.map((file) => ({
        id:
          typeof crypto !== "undefined" && crypto.randomUUID
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random()}`,
        file,
        url: URL.createObjectURL(file),
      })),
    ]);
  };

  const removePhoto = (photoId: string) => {
    setPhotos((prev) => {
      const target = prev.find((p) => p.id === photoId);
      if (target?.url) {
        try {
          URL.revokeObjectURL(target.url);
        } catch {
          // ignore
        }
      }
      return prev.filter((p) => p.id !== photoId);
    });
  };

  const allFieldsFilled = Boolean(pros.trim() && cons.trim() && comment.trim());
  const canSubmit = rating > 0 && allFieldsFilled;

  return (
    <div className="tg-viewport">
      <main className={styles.root}>
        <h1 className={styles.title}>Оцените товар</h1>

        <section className={styles.productRow}>
          <div className={styles.thumbWrap}>
            {resolvedImage ? (
              <img
                src={resolvedImage}
                alt={product?.name ?? ""}
                className={styles.thumb}
              />
            ) : (
              <div className={styles.thumbFallback} />
            )}
          </div>
          <div className={styles.productMeta}>
            <div className={styles.productName}>{product?.name ?? ""}</div>
            <div className={styles.productSub}>
              Размер: <span>L</span> &nbsp; &middot; Артикул: <span>4465457</span>
            </div>
            <div className={styles.productPrice}>{product?.price ?? ""}</div>
          </div>
        </section>

        <div className={styles.starsRow} aria-label="Оценка" role="group">
          {Array.from({ length: 5 }).map((_, i) => {
            const value = i + 1;
            const active = value <= rating;
            return (
              <button
                key={value}
                type="button"
                className={styles.starBtn}
                aria-label={`Оценить на ${value}`}
                aria-pressed={active}
                onClick={() => setRating(value)}
              >
                <img
                  src="/icons/product/Star.svg"
                  alt=""
                  aria-hidden="true"
                  className={active ? styles.starActive : styles.star}
                />
              </button>
            );
          })}
        </div>

        <div className={styles.form}>
          <div
            className={styles.prosWrap}
            data-filled={pros ? "true" : "false"}
          >
            <div className={styles.prosLabel}>Достоинства</div>
            <textarea
              ref={prosRef}
              className={styles.prosInput}
              aria-label="Достоинства"
              value={pros}
              onChange={(e) => setPros(e.target.value)}
              onInput={(e) => autosize(e.currentTarget)}
              rows={1}
            />
            {pros ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Очистить"
                onClick={() => setPros("")}
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

          <div
            className={styles.fieldWrap}
            data-filled={cons ? "true" : "false"}
          >
            <div className={styles.fieldLabel}>Недостатки</div>
            <textarea
              ref={consRef}
              className={styles.fieldInput}
              aria-label="Недостатки"
              value={cons}
              onChange={(e) => setCons(e.target.value)}
              onInput={(e) => autosize(e.currentTarget)}
              rows={1}
            />
            {cons ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Очистить недостатки"
                onClick={() => setCons("")}
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

          <div
            className={styles.fieldWrap}
            data-filled={comment ? "true" : "false"}
          >
            <div className={styles.fieldLabel}>Комментарий</div>
            <textarea
              ref={commentRef}
              className={styles.fieldInput}
              aria-label="Комментарий"
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
                onClick={() => setComment("")}
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

          <div className={styles.photosRow}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className={styles.fileInput}
              onChange={(e) => {
                addPhotos(e.target.files);
                e.target.value = "";
              }}
            />

            <button
              type="button"
              className={styles.photoTile}
              onClick={() => fileInputRef.current?.click()}
            >
              <img
                src="/icons/global/uploadImage.svg"
                alt=""
                aria-hidden="true"
                className={styles.photoIcon}
              />
              <p className={styles.photoLabel}>Фото</p>
            </button>

            {photos.map((p) => (
              <div key={p.id} className={styles.photoThumb}>
                <img src={p.url} alt="" className={styles.photoImg} />
                <button
                  type="button"
                  className={styles.removeBtn}
                  aria-label="Удалить фото"
                  onClick={() => removePhoto(p.id)}
                >
                  <img
                    src="/icons/global/closeWhite.svg"
                    alt=""
                    aria-hidden="true"
                    className={styles.removeIcon}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.bottomBar}>
          <button
            type="button"
            className={canSubmit ? styles.submitBtn : styles.submitBtnDisabled}
            disabled={!canSubmit}
            onClick={() => {
              // TODO: send to API when backend exists
              router.back();
            }}
          >
            Отправить
          </button>
        </div>
      </main>
    </div>
  );
}
