"use client";
import React, { useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import styles from "./ProductReviews.module.css";
import cx from "clsx";

interface Review {
  id: string | number;
  avatar: string;
  rating: number;
  productName?: string;
  userName: string;
  date: string;
  pros: string;
  cons: string;
}

interface RatingDistribution {
  [key: number]: number;
}

interface ProductReviewsProps {
  brandName?: string;
  reviews?: Review[];
  ratingDistribution?: RatingDistribution;
  productImages?: string[];
  onViewAll?: () => void;
}

function toBrandSlug(value: unknown): string {
  const raw = String(value ?? "")
    .trim()
    .toLowerCase();
  if (!raw) return "";
  return raw.replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
}

export default function ProductReviews({
  brandName,
  reviews = [],
  ratingDistribution = {},
  productImages = [],
  onViewAll,
}: ProductReviewsProps) {
  // Расчет общего рейтинга и количества отзывов
  const { averageRating, totalReviews } = useMemo(() => {
    const dist = ratingDistribution as Record<number, number>;
    const r5 = dist[5] ?? 0;
    const r4 = dist[4] ?? 0;
    const r3 = dist[3] ?? 0;
    const r2 = dist[2] ?? 0;
    const r1 = dist[1] ?? 0;
    const total = r5 + r4 + r3 + r2 + r1;
    const sum = r5 * 5 + r4 * 4 + r3 * 3 + r2 * 2 + r1 * 1;
    const average = total > 0 ? sum / total : 0;
    return {
      averageRating: Math.round(average * 10) / 10,
      totalReviews: total,
    };
  }, [ratingDistribution]);

  // Рендер звезд
  const renderStars = (rating: number, size: number = 12, showEmpty: boolean = true) => {
    const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
    const starsToRender = showEmpty ? 5 : safeRating;
    return (
      <div className={styles.stars} aria-label={`\u0420\u0435\u0439\u0442\u0438\u043d\u0433 ${safeRating} \u0438\u0437 5`}>
        {Array.from({ length: starsToRender }, (_, i) => i + 1).map((star) => (
          <img key={star} src="/icons/product/Star.svg" alt="star" />
        ))}
      </div>
    );
  };

  // Рендер гистограммы рейтинга (вертикальная стопка горизонтальных баров)
  const renderRatingBars = () => {
    const dist = ratingDistribution as Record<number, number>;
    const r5 = dist[5] ?? 0;
    const r4 = dist[4] ?? 0;
    const r3 = dist[3] ?? 0;
    const r2 = dist[2] ?? 0;
    const r1 = dist[1] ?? 0;
    const maxCount = Math.max(r5, r4, r3, r2, r1);

    const bars = [
      { stars: 5, count: r5 },
      { stars: 4, count: r4 },
      { stars: 3, count: r3 },
      { stars: 2, count: r2 },
      { stars: 1, count: r1 },
    ];

    return (
      <div className={styles.bars} aria-label="\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0440\u0435\u0439\u0442\u0438\u043d\u0433\u043e\u0432">
        {bars.map((bar) => {
          const width = maxCount > 0 ? (bar.count / maxCount) * 100 : 0;

          return (
            <div key={bar.stars} className={styles.barRow}>
              <div className={styles.barStars} aria-hidden="true">
                {renderStars(bar.stars, 10, false)}
              </div>
              <div className={styles.barTrack} aria-hidden="true">
                <div
                  className={styles.barFill}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const brandSlug = toBrandSlug(brandName);
  const reviewsHref = brandSlug
    ? `/profile/reviews/${encodeURIComponent(brandSlug)}`
    : "/profile/reviews";
  const previewImages = Array.isArray(productImages)
    ? productImages.slice(0, 2)
    : [];

  return (
    <section className={styles.outer}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h2 className={styles.title}>\u041e\u0442\u0437\u044b\u0432\u044b \u043d\u0430 {brandName}</h2>
          <Link
            href={reviewsHref}
            onClick={onViewAll}
            className={styles.chevron}
            aria-label="\u0412\u0441\u0435 \u043e\u0442\u0437\u044b\u0432\u044b"
          >
            <Image
              src="/icons/global/arrowBlack.svg"
              alt=""
              width={7}
              height={11}
            />
          </Link>
        </div>

        <div className={styles.summary}>
          <div className={styles.ratingBlock}>
            <div className={styles.ratingRow}>
              <span className={styles.ratingValue}>{averageRating}</span>
              <img
                src="/icons/product/Star.svg"
                alt="star"
                style={{ width: "14px", height: "14px" }}
              />
            </div>
            <span className={styles.ratingCount}>
              {totalReviews}{" "}
              {totalReviews === 1
                ? "\u043e\u0442\u0437\u044b\u0432"
                : totalReviews < 5
                  ? "\u043e\u0442\u0437\u044b\u0432\u0430"
                  : "\u043e\u0442\u0437\u044b\u0432\u043e\u0432"}
            </span>
          </div>

          <div className={styles.barsBlock}>{renderRatingBars()}</div>

          {previewImages.length > 0 ? (
            <div className={styles.previewImages} aria-hidden="true">
              {previewImages.map((src, idx) => (
                <span
                  key={`${src}-${idx}`}
                  className={cx(
                    styles.previewImgWrap,
                    idx === 1 && styles.previewImgSecond,
                  )}
                >
                  <Image
                    src={src}
                    alt=""
                    fill
                    className={styles.previewImg}
                    sizes="56px"
                  />
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className={styles.divider} aria-hidden="true" />

        <div className={cx(styles.scroller, "scrollbar-hide")}>
          <div className={styles.reviewsRow}>
            {Array.isArray(reviews) && reviews.length > 0
              ? reviews.map((review) => (
                  <article key={review.id} className={styles.reviewCard}>
                    <div className={styles.reviewHeader}>
                      <span className={styles.avatar} aria-hidden="true">
                        <Image
                          src={review.avatar}
                          alt=""
                          fill
                          className={styles.avatarImg}
                          sizes="32px"
                        />
                      </span>

                      <div className={styles.reviewMeta}>
                        <div className={styles.reviewTopLine}>
                          {renderStars(review.rating, 12)}
                          {review.productName ? (
                            <span className={styles.productName}>
                              {review.productName}
                            </span>
                          ) : null}
                        </div>

                        <div className={styles.reviewSubLine}>
                          <span className={styles.metaText}>
                            {review.userName}
                          </span>
                          <span className={styles.metaDot} aria-hidden="true" />
                          <span className={styles.metaText}>{review.date}</span>
                        </div>
                      </div>
                    </div>

                    <div className={styles.reviewBody}>
                      <p className={styles.reviewText}>
                        <span className={styles.reviewLabel}>\u0414\u043e\u0441\u0442\u043e\u0438\u043d\u0441\u0442\u0432\u0430:</span>{" "}
                        {review.pros}
                      </p>
                      <p className={styles.reviewText}>
                        <span className={styles.reviewLabel}>\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043a\u0438:</span>{" "}
                        {review.cons}
                      </p>
                    </div>
                  </article>
                ))
              : null}
          </div>
        </div>
      </div>
    </section>
  );
}
