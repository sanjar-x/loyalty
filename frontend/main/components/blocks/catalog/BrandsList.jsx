"use client";
import Image from "next/image";
import { useMemo } from "react";

import { useGetBrandsQuery } from "@/lib/store/api";

import styles from "./BrandsList.module.css";

function getLetter(name) {
  const raw = typeof name === "string" ? name.trim() : "";
  const first = raw ? raw[0] : "";
  return first ? first.toUpperCase() : "#";
}

function groupBrands(brands) {
  const rows = Array.isArray(brands) ? brands : [];
  const sorted = [...rows].sort((a, b) =>
    String(a?.name || "").localeCompare(String(b?.name || ""), "ru", {
      sensitivity: "base",
    }),
  );

  const map = new Map();
  for (const b of sorted) {
    const id = b?.id;
    const name = b?.name ?? "";
    if (id == null || !name) continue;
    const letter = getLetter(name);
    if (!map.has(letter)) map.set(letter, []);
    map.get(letter).push({ id, name });
  }

  return Array.from(map.entries()).map(([letter, items]) => ({
    letter,
    brands: items,
  }));
}

export default function BrandsList() {
  const { data: brandsData, isLoading } = useGetBrandsQuery();

  const groups = useMemo(() => groupBrands(brandsData), [brandsData]);

  if (isLoading) {
    return (
      <div className={styles.root} aria-busy="true">
        <div className={styles.groups}>
          {Array.from({ length: 3 }).map((_, gIdx) => (
            <div key={gIdx} className={styles.group} aria-hidden="true">
              <div className={styles.letterBar}>
                <div className={styles.skeletonLetter} />
              </div>

              <div className={styles.list}>
                {Array.from({ length: 5 }).map((_, iIdx) => (
                  <div key={iIdx}>
                    <div className={styles.item}>
                      <div className={styles.skeletonName} />
                      <div className={styles.chevron}>
                        <div className={styles.skeletonChevron} />
                      </div>
                    </div>
                    {iIdx < 4 ? <div className={styles.divider} /> : null}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <div className={styles.groups}>
        {groups.map((group) => (
          <div key={group.letter} className={styles.group}>
            {/* Буква */}
            <div className={styles.letterBar}>
              <span className={styles.letter}>{group.letter}</span>
            </div>

            {/* Список брендов */}
            <div className={styles.list}>
              {group.brands.map((brand, brandIndex) => (
                <div key={brand.id}>
                  <div className={styles.item}>
                    <span className={styles.name}>{brand.name}</span>
                    <div className={styles.chevron}>
                      <Image
                        src="/icons/global/arrowBlack.svg"
                        alt=""
                        width={7}
                        height={11}
                      />
                    </div>
                  </div>
                  {brandIndex < group.brands.length - 1 && (
                    <div className={styles.divider} />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
