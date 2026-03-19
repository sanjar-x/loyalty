"use client";
import React from "react";
import styles from "./AllBrandsList.module.css";
import cx from "clsx";

function getLetter(name) {
  const raw = typeof name === "string" ? name.trim() : "";
  const first = raw ? raw[0] : "";
  return first ? first.toUpperCase() : "#";
}

export default function AllBrandsList({ brands, onToggleFavorite }) {
  const sorted = Array.isArray(brands)
    ? [...brands].sort((a, b) =>
        String(a?.name || "").localeCompare(String(b?.name || "")),
      )
    : [];

  return (
    <ul className={cx(styles.c1, styles.tw1)}>
      {sorted.map((brand, index) => {
        const letter = getLetter(brand?.name);
        const prev = index > 0 ? sorted[index - 1] : null;
        const prevLetter = prev ? getLetter(prev?.name) : null;
        const showLetter = letter !== prevLetter;

        return (
          <React.Fragment key={brand.id}>
            {showLetter ? (
              <li className={styles.letterRow} aria-hidden="true">
                {letter}
              </li>
            ) : null}

            <li className={cx(styles.c2, styles.tw2)}>
              <div className={cx(styles.c3, styles.tw3)}>
                {brand.image ? (
                  <div className={cx(styles.c4, styles.tw4)}>
                    <img
                      src={brand.image}
                      alt={brand.name}
                      className={styles.c5}
                    />
                  </div>
                ) : null}

                <div className={cx(styles.c6, styles.tw5)}>
                  <span className={styles.c7}>{brand.name}</span>
                  <span className={styles.c8}>Бренд</span>
                </div>
              </div>

              {onToggleFavorite ? (
                <button
                  type="button"
                  onClick={() => onToggleFavorite(brand.id)}
                  className={cx(styles.c9, styles.tw6)}
                  aria-pressed={brand.isFavorite}
                >
                  <img
                    src={
                      brand.isFavorite
                        ? "/icons/global/active-heart.svg"
                        : "/icons/global/not-active-heart.svg"
                    }
                    alt={
                      brand.isFavorite
                        ? "Удалить из избранного"
                        : "Добавить в избранное"
                    }
                    className={styles.c10}
                  />
                </button>
              ) : null}
            </li>
          </React.Fragment>
        );
      })}
    </ul>
  );
}
