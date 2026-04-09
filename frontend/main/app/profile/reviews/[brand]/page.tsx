"use client";

import React, { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import styles from "./page.module.css";
import BottomSheet from "@/components/ui/BottomSheet";
import Footer from "@/components/layout/Footer";

function titleize(value: string | string[] | undefined) {
  const s = String(value || "")
    .replace(/[-_]+/g, " ")
    .trim();
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function toNumber(value: unknown) {
  const digits = String(value ?? "").replace(/[^0-9]/g, "");
  const n = Number(digits);
  return Number.isFinite(n) ? n : 0;
}

function formatRub(value: number | string) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return "";
  return `${n.toLocaleString("ru-RU")} ₽`;
}

function Stars({ value, size = 12, showEmpty = true }: { value: number; size?: number; showEmpty?: boolean }) {
  const safe = Math.max(0, Math.min(5, Number(value) || 0));
  const starsToRender = showEmpty ? 5 : safe;

  return (
    <div className={styles.stars} aria-label={`Рейтинг ${safe} из 5`}>
      {Array.from({ length: starsToRender }, (_, i) => i + 1).map((star) => (
        <img
          key={star}
          src="/icons/product/Star.svg"
          alt="star"
          className={styles.star}
          style={{ width: `${size}px`, height: `${size}px` }}
        />
      ))}
    </div>
  );
}

function Segmented({ value, onChange, items }: { value: string; onChange: (v: string) => void; items: { value: string; label: string }[] }) {
  return (
    <div
      className={styles.segmented}
      role="tablist"
      aria-label="Фильтр отзывов"
    >
      {items.map((it: { value: string; label: string }) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={active}
            className={`${styles.segment} ${active ? styles.segmentActive : ""}`}
            onClick={() => onChange?.(it.value)}
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

function Chip({ active, onClick, icon, children, ignoreActive = false }: { active: boolean; onClick: () => void; icon?: React.ReactNode; children: React.ReactNode; ignoreActive?: boolean }) {
  const isActive = !ignoreActive && !!active;
  return (
    <button
      type="button"
      className={`${styles.chip} ${isActive ? styles.chipActive : ""}`}
      aria-pressed={isActive}
      onClick={onClick}
    >
      {icon ? <span className={styles.chipIcon}>{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}

function ReviewPhotos({ images = [] }: { images?: string[] }) {
  if (!Array.isArray(images) || images.length === 0) return null;

  return (
    <div className={styles.photoRow} aria-label="Фото">
      {images.slice(0, 4).map((src, idx) => (
        <div key={`${src}-${idx}`} className={styles.photoWrap}>
          {/* local assets: /public/products/... */}
          <img src={src} alt="" className={styles.photoImg} />
        </div>
      ))}
    </div>
  );
}

function ExpandableReviewText({ label, text, clampLines = 3 }: { label: string; text: string; clampLines?: number }) {
  const [expanded, setExpanded] = useState(false);
  const content = String(text ?? "").trim();
  if (!content) return null;

  const isLong = content.length > 120;

  return (
    <div className={styles.reviewTextBlock}>
      <p
        className={`${styles.reviewText} ${!expanded && isLong ? styles.reviewTextClamp : ""}`}
        style={{ WebkitLineClamp: clampLines }}
      >
        <span className={styles.reviewLabel}>{label}:</span> {content}
      </p>
      {isLong ? (
        <button
          type="button"
          className={styles.textMoreBtn}
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Скрыть" : "ещё"}
        </button>
      ) : null}
    </div>
  );
}

interface ReviewData {
  id: number;
  userName: string;
  avatar: string;
  date: string;
  rating: number;
  isVariant?: boolean;
  images?: string[];
  pros: string;
  cons: string;
  comment?: string;
  product?: {
    name: string;
    size?: string;
    article?: string;
    image: string;
  };
}

function ReviewCard({ review }: { review: ReviewData }) {
  return (
    <article className={styles.reviewCard}>
      <div className={styles.reviewHeader}>
        <div className={styles.avatarWrap} aria-hidden="true">
          <img src={review.avatar} alt="" className={styles.avatarImg} />
        </div>

        <div className={styles.reviewMeta}>
          <div className={styles.reviewTopLine}>
            <Stars value={review.rating} size={16} />
          </div>
          <div className={styles.reviewSubLine}>
            <span className={styles.metaText}>{review.userName}</span>
            <span className={styles.dot} aria-hidden="true" />
            <span className={styles.metaText2}>{review.date}</span>
          </div>
        </div>
      </div>

      <ReviewPhotos images={review.images} />

      <div className={styles.reviewBody}>
        <ExpandableReviewText label="Достоинства" text={review.pros} />
        <ExpandableReviewText label="Недостатки" text={review.cons} />
        <ExpandableReviewText label="Комментарий" text={review.comment ?? ""} />
      </div>

      {review.product ? (
        <div className={styles.productRow}>
          <div className={styles.productThumb} aria-hidden="true">
            <img
              src={review.product.image}
              alt=""
              className={styles.productThumbImg}
            />
          </div>
          <div className={styles.productMeta}>
            <div className={styles.productName}>{review.product.name}</div>
            <div className={styles.productSub}>
              Размер:{" "}
              <span>
                {review.product.size ? `${review.product.size}` : null}
              </span>{" "}
              · {review.product.size && review.product.article ? "" : null}
              Артикул:{" "}
              <span>
                {review.product.article ? `${review.product.article}` : null}
              </span>
            </div>
          </div>
        </div>
      ) : null}
    </article>
  );
}

export default function BrandReviewsPage() {
  const router = useRouter();
  const params = useParams();

  const brand = titleize(params?.brand);

  // Mock: bu yer keyin API bilan almashtiriladi
  const { priceRub, averageRating, totalReviews, ratingBars, reviews } =
    useMemo(() => {
      const priceRub = 2890;

      const reviews = [
        {
          id: 1,
          userName: "Анастасия",
          avatar: "https://i.pravatar.cc/150?img=1",
          date: "21 апреля",
          rating: 5,
          isVariant: true,
          images: [
            "/products/shoes-1.png",
            "/products/shoes-2.png",
            "/products/shoes-1.png",
          ],
          pros: "стильно, классика которую можно носить под разный стиль одежды",
          cons: "помятая коробка",
          comment: "ткань отличная :3",
          product: {
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            image: "/products/t-shirt-1.png",
          },
        },
        {
          id: 2,
          userName: "Анастасия",
          avatar: "https://i.pravatar.cc/150?img=1",
          date: "21 апреля",
          rating: 5,
          isVariant: false,
          images: ["/products/shoes-2.png", "/products/shoes-1.png"],
          pros: "стильно, классика которую можно носить под разный стиль одежды",
          cons: "помятая коробка",
          comment: "ткань отличная :3 сервис лоялти...",
          product: {
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            image: "/products/t-shirt-2.png",
          },
        },
        {
          id: 3,
          userName: "Анастасия",
          avatar: "https://i.pravatar.cc/150?img=1",
          date: "21 апреля",
          rating: 4,
          isVariant: true,
          images: [],
          pros: "их нет",
          cons: "не очень",
          comment: "ткань плохая верните деньги",
          product: {
            name: "Джинсы Carne Bollente",
            size: "L",
            article: "4465457",
            image: "/products/t-shirt-1.png",
          },
        },
      ];

      const totalReviews = 84;
      const averageRating = 4.5;

      const ratingBars = [
        { stars: 5, value: 0.62 },
        { stars: 4, value: 0.24 },
        { stars: 3, value: 0.08 },
        { stars: 2, value: 0.04 },
        { stars: 1, value: 0.02 },
      ];

      return { priceRub, averageRating, totalReviews, ratingBars, reviews };
    }, []);

  const [tab, setTab] = useState("all");
  const [onlyPhoto, setOnlyPhoto] = useState(false);
  const [sortMode, setSortMode] = useState("new");
  const [sortSheetOpen, setSortSheetOpen] = useState(false);
  const [sortDraft, setSortDraft] = useState(sortMode);

  const sortOptions = useMemo(
    () => [
      { value: "new", label: "Новые" },
      { value: "old", label: "Старые" },
      { value: "high", label: "С высокой оценкой" },
      { value: "low", label: "С низкой оценкой" },
    ],
    [],
  );

  const sortLabel = useMemo(() => {
    const found = sortOptions.find((o) => o.value === sortMode);
    return found?.label || "Новые";
  }, [sortMode, sortOptions]);

  const filtered = useMemo(() => {
    let list = reviews;

    if (tab === "variant") list = list.filter((r) => r.isVariant);
    if (onlyPhoto)
      list = list.filter((r) => Array.isArray(r.images) && r.images.length > 0);

    if (sortMode === "new") return list;
    if (sortMode === "old") return [...list].reverse();

    const scored = [...list].map((r) => ({
      r,
      rating: Number(r?.rating) || 0,
    }));
    if (sortMode === "high") {
      scored.sort((a, b) => b.rating - a.rating);
      return scored.map((x) => x.r);
    }
    if (sortMode === "low") {
      scored.sort((a, b) => a.rating - b.rating);
      return scored.map((x) => x.r);
    }

    return list;
  }, [onlyPhoto, reviews, sortMode, tab]);

  return (
    <>
      <div className={styles.page}>
        <div className={styles.topbarTitle}>Отзывы</div>

        <main className={styles.main}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryTop}>
              <div className={styles.ratingLeft}>
                <div className={styles.ratingValueRow}>
                  <span className={styles.ratingValue}>
                    {averageRating.toFixed(1)}
                  </span>
                  <img
                    src="/icons/product/Star.svg"
                    alt="starSvgICon"
                    className={styles.ratingPlusStart}
                  />
                </div>
                <div className={styles.ratingSub}>{totalReviews} отзыва</div>
              </div>
              <div
                className={styles.ratingBars}
                aria-label="Распределение рейтингов"
              >
                {ratingBars.map((b) => (
                  <div key={b.stars} className={styles.ratingBarRow}>
                    <div className={styles.ratingBarStars} aria-hidden="true">
                      <Stars value={b.stars} size={10} showEmpty={false} />
                    </div>
                    <div className={styles.ratingBarTrack} aria-hidden="true">
                      <div
                        className={styles.ratingBarFill}
                        style={{ width: `${Math.round(b.value * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Segmented
              value={tab}
              onChange={setTab}
              items={[
                { value: "all", label: "Все отзывы" },
                { value: "variant", label: "Этот вариант" },
              ]}
            />

            <div className={styles.previewStrip} aria-hidden="true">
              {[
                "/products/shoes-1.png",
                "/products/shoes-2.png",
                "/products/shoes-1.png",
                "/products/shoes-2.png",
              ].map((src, idx) => (
                <div key={`${src}-${idx}`} className={styles.previewItem}>
                  <img src={src} alt="" className={styles.previewImg} />
                </div>
              ))}
            </div>

            <div className={styles.chipsRow}>
              <Chip
                active={false}
                onClick={() => {
                  setSortDraft(sortMode);
                  setSortSheetOpen(true);
                }}
                ignoreActive
                icon={
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M4 6h16M4 12h10M4 18h16"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                }
              >
                {sortLabel}
              </Chip>
              <Chip active={onlyPhoto} onClick={() => setOnlyPhoto((v) => !v)}>
                Только с фото
              </Chip>
            </div>
          </div>

          <BottomSheet
            open={sortSheetOpen}
            onClose={() => {
              setSortSheetOpen(false);
              setSortDraft(sortMode);
            }}
            title="Показывать сначала"
            footer={
              <div className={styles.sheetFooterRow}>
                <button
                  type="button"
                  className={styles.sheetCancelBtn}
                  onClick={() => {
                    setSortSheetOpen(false);
                    setSortDraft(sortMode);
                  }}
                >
                  Отменить
                </button>
                <button
                  type="button"
                  className={styles.sheetApplyBtn}
                  onClick={() => {
                    setSortMode(sortDraft);
                    setSortSheetOpen(false);
                  }}
                >
                  Применить
                </button>
              </div>
            }
          >
            <div className={styles.sheetList} aria-label="Сортировка">
              {sortOptions.map((opt) => {
                const selected = opt.value === sortDraft;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    className={styles.sheetRow}
                    onClick={() => setSortDraft(opt.value)}
                  >
                    <span className={styles.sheetLabel}>{opt.label}</span>
                    <span
                      className={
                        selected
                          ? styles.sheetControlSelected
                          : styles.sheetControlUnselected
                      }
                      aria-hidden="true"
                    >
                      {selected ? (
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <path
                            d="M20 6L9 17l-5-5"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      ) : null}
                    </span>
                  </button>
                );
              })}
            </div>
          </BottomSheet>

          <div className={styles.list}>
            {filtered.length ? (
              filtered.map((r) => <ReviewCard key={r.id} review={r} />)
            ) : (
              <div
                className={styles.emptyCard}
                role="status"
                aria-live="polite"
              >
                <div className={styles.emptyTitle}>Здесь пока нет отзывов</div>
                <button
                  type="button"
                  className={styles.emptyHint}
                  onClick={() => setTab("all")}
                >
                  Но вы можете посмотреть все отзывы
                </button>
              </div>
            )}
          </div>

          <div className={styles.brandHint}>
            {brand ? `Отзывы бренда ${brand}` : "Отзывы"}
          </div>
        </main>

        <div className={styles.bottomBar}>
          <button
            type="button"
            className={`${styles.bottomBtn} ${styles.bottomBtnPrimary}`}
            onClick={() => console.log("buyNow", { brand })}
          >
            Купить сейчас
          </button>
          <button
            type="button"
            className={`${styles.bottomBtn} ${styles.bottomBtnSecondary}`}
            onClick={() => console.log("addToCart", { brand, priceRub })}
          >
            В корзину
          </button>
        </div>
      </div>

      <Footer />
    </>
  );
}
