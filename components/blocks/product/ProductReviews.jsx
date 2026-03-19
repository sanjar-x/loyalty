"use client";
import React, { useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import styles from "./ProductReviews.module.css";
import cx from "clsx";

function toBrandSlug(value) {
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
}) {
  // Расчет общего рейтинга и количества отзывов
  const { averageRating, totalReviews } = useMemo(() => {
    const {
      5: r5 = 0,
      4: r4 = 0,
      3: r3 = 0,
      2: r2 = 0,
      1: r1 = 0,
    } = ratingDistribution;
    const total = r5 + r4 + r3 + r2 + r1;
    const sum = r5 * 5 + r4 * 4 + r3 * 3 + r2 * 2 + r1 * 1;
    const average = total > 0 ? sum / total : 0;
    return {
      averageRating: Math.round(average * 10) / 10,
      totalReviews: total,
    };
  }, [ratingDistribution]);

  // Рендер звезд
  const renderStars = (rating, size = 12, showEmpty = true) => {
    const safeRating = Math.max(0, Math.min(5, Number(rating) || 0));
    const starsToRender = showEmpty ? 5 : safeRating;
    return (
      <div className={styles.stars} aria-label={`Рейтинг ${safeRating} из 5`}>
        {Array.from({ length: starsToRender }, (_, i) => i + 1).map((star) => (
          <img key={star} src="/icons/product/Star.svg" alt="star" />
        ))}
      </div>
    );
  };

  // Рендер гистограммы рейтинга (вертикальная стопка горизонтальных баров)
  const renderRatingBars = () => {
    const {
      5: r5 = 0,
      4: r4 = 0,
      3: r3 = 0,
      2: r2 = 0,
      1: r1 = 0,
    } = ratingDistribution;
    const maxCount = Math.max(r5, r4, r3, r2, r1);

    const bars = [
      { stars: 5, count: r5 },
      { stars: 4, count: r4 },
      { stars: 3, count: r3 },
      { stars: 2, count: r2 },
      { stars: 1, count: r1 },
    ];

    return (
      <div className={styles.bars} aria-label="Распределение рейтингов">
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
          <h2 className={styles.title}>Отзывы на {brandName}</h2>
          <Link
            href={reviewsHref}
            onClick={onViewAll}
            className={styles.chevron}
            aria-label="Все отзывы"
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
                ? "отзыв"
                : totalReviews < 5
                  ? "отзыва"
                  : "отзывов"}
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
                        <span className={styles.reviewLabel}>Достоинства:</span>{" "}
                        {review.pros}
                      </p>
                      <p className={styles.reviewText}>
                        <span className={styles.reviewLabel}>Недостатки:</span>{" "}
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
