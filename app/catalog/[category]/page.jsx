"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import SearchBar from "@/components/blocks/search/SearchBar";

import { useGetCategoriesWithTypesQuery } from "@/lib/store/api";

import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import CatalogTabs from "@/components/blocks/catalog/CatalogTabs";
import BrandsList from "@/components/blocks/catalog/BrandsList";

import styles from "./page.module.css";

const normalize = (v) =>
  String(v ?? "")
    .trim()
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/[\s_-]+/g, "");

function safeDecode(value) {
  const s = String(value ?? "");
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}

export default function CategoryPage() {
  const params = useParams();
  const categoryParamRaw = params?.category;
  const categoryParam = safeDecode(categoryParamRaw);

  const {
    data: categoriesWithTypes,
    isLoading,
    isError,
  } = useGetCategoriesWithTypesQuery();

  const legacyNameByKey = {
    clothes: "Одежда",
    shoes: "Обувь",
    accessories: "Аксессуры",
  };

  const resolvedKey =
    typeof categoryParam === "string" && legacyNameByKey[categoryParam]
      ? legacyNameByKey[categoryParam]
      : categoryParam;

  const resolvedKeyNorm = normalize(resolvedKey);

  const category = Array.isArray(categoriesWithTypes)
    ? categoriesWithTypes.find((c) => {
        if (!c || typeof c !== "object") return false;
        const idMatch =
          typeof resolvedKey === "string" &&
          /^\d+$/.test(resolvedKey) &&
          String(c.id) === resolvedKey;
        if (idMatch) return true;
        return normalize(c.name) === resolvedKeyNorm;
      })
    : null;

  const types = Array.isArray(category?.types) ? category.types : [];
  const [activeTab, setActiveTab] = useState("catalog");

  if (isLoading) {
    return (
      <div className={styles.root}>
        <h3 className={styles.searchTitle}>Каталог</h3>
        <SearchBar />
        <main className={styles.main}>
          <div className={styles.sectionHeader} aria-hidden="true">
            <div className={styles.headerRow}>
              <div className={styles.skeletonTitle} />
              <button type="button" className={styles.allBtn}>
                <span className={styles.allText}>все</span>
                <div className={styles.allIconWrap}>
                  <Image
                    src="/icons/global/Wrap.svg"
                    alt=""
                    width={20}
                    height={18}
                  />
                </div>
              </button>
            </div>
          </div>

          <div className={styles.listOuter} aria-busy="true">
            <div className={styles.list}>
              <div className={`${styles.divider} ${styles.dividerTop}`} />

              <div className={styles.items}>
                {Array.from({ length: 10 }).map((_, idx) => (
                  <div key={idx}>
                    <div className={styles.itemRow}>
                      <div className={styles.skeletonType} />
                      <div className={styles.chevron}>
                        <div className={styles.skeletonChevron} />
                      </div>
                    </div>
                    {idx < 9 ? <div className={styles.divider} /> : null}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (isError || !category) {
    return (
      <div className={styles.error}>
        <p>Категория не найдена</p>
      </div>
    );
  }

  return (
    <div className={styles.root}>
      <h3 className={styles.searchTitle}>Каталог</h3>
      <SearchBar />

      <main className={styles.main}>
        {activeTab === "catalog" ? (
          <>
            {/* Заголовок категории и кнопка "все" */}
            <div className={styles.sectionHeader}>
              <div className={styles.headerRow}>
                <h1 className={styles.title}>{category?.name}</h1>
                <button type="button" className={styles.allBtn}>
                  <span className={styles.allText}>все</span>
                  <div className={styles.allIconWrap}>
                    <Image
                      src="/icons/global/Wrap.svg"
                      alt=""
                      width={20}
                      height={18}
                    />
                  </div>
                </button>
              </div>
            </div>

            <div className={styles.listOuter}>
              <div className={styles.list}>
                <div className={`${styles.divider} ${styles.dividerTop}`} />

                <div className={styles.items}>
                  {types.map((t, index) => (
                    <div key={t?.id ?? t?.name ?? index}>
                      <div className={styles.itemRow}>
                        <span className={styles.subcategory}>{t?.name}</span>
                        <div className={styles.chevron}>
                          <Image
                            src="/icons/global/arrowBlack.svg"
                            alt=""
                            width={7}
                            height={11}
                          />
                        </div>
                      </div>
                      {index < types.length - 1 && (
                        <div className={styles.divider} />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        ) : (
          <BrandsList />
        )}
      </main>
      <Footer />
    </div>
  );
}
