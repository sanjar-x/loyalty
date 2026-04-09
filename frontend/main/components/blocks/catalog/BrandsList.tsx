"use client";
import Image from "next/image";
import { useMemo } from "react";

import styles from "./BrandsList.module.css";

interface BrandItem {
  id: string | number;
  name: string;
}

interface BrandGroup {
  letter: string;
  brands: BrandItem[];
}

function getLetter(name: unknown): string {
  const raw = typeof name === "string" ? name.trim() : "";
  const first = raw ? raw[0] : "";
  return first ? first.toUpperCase() : "#";
}

function groupBrands(brands: unknown[]): BrandGroup[] {
  const rows = Array.isArray(brands) ? brands : [];
  const sorted = [...rows].sort((a, b) => {
    const aObj = a as Record<string, unknown>;
    const bObj = b as Record<string, unknown>;
    return String(aObj?.name || "").localeCompare(String(bObj?.name || ""), "ru", {
      sensitivity: "base",
    });
  });

  const map = new Map<string, BrandItem[]>();
  for (const b of sorted) {
    const bObj = b as Record<string, unknown>;
    const id = bObj?.id;
    const name = (bObj?.name as string) ?? "";
    if (id == null || !name) continue;
    const letter = getLetter(name);
    if (!map.has(letter)) map.set(letter, []);
    map.get(letter)!.push({ id: id as string | number, name });
  }

  return Array.from(map.entries()).map(([letter, items]) => ({
    letter,
    brands: items,
  }));
}

export default function BrandsList() {
  // TODO: подключить API
  const brandsData: unknown[] = [];
  const isLoading = false;

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
            <div className={styles.letterBar}>
              <span className={styles.letter}>{group.letter}</span>
            </div>

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
