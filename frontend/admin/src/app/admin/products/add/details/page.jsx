import Link from 'next/link';
import ProductDetailsForm from './ProductDetailsForm';
import { findProductCategoryPath } from '@/services/categories';
import styles from './page.module.css';

function BackArrowIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M11.9621 6.4751C12.1996 6.4751 12.4371 6.5626 12.6246 6.7501C12.9871 7.1126 12.9871 7.7126 12.6246 8.0751L5.69961 15.0001L12.6246 21.9251C12.9871 22.2876 12.9871 22.8876 12.6246 23.2501C12.2621 23.6126 11.6621 23.6126 11.2996 23.2501L3.71211 15.6626C3.34961 15.3001 3.34961 14.7001 3.71211 14.3376L11.2996 6.7501C11.4871 6.5626 11.7246 6.4751 11.9621 6.4751Z"
        fill="black"
      />
      <path
        d="M4.5875 14.0625L25.625 14.0625C26.1375 14.0625 26.5625 14.4875 26.5625 15C26.5625 15.5125 26.1375 15.9375 25.625 15.9375L4.5875 15.9375C4.075 15.9375 3.65 15.5125 3.65 15C3.65 14.4875 4.075 14.0625 4.5875 14.0625Z"
        fill="black"
      />
    </svg>
  );
}

function Crumb({ label }) {
  return (
    <div className={styles.crumb}>
      <span className={styles.crumbLabel}>{label}</span>
      <span className={styles.crumbChevron}>
        <svg
          width="9"
          height="16"
          viewBox="0 0 9 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M0.277478 15.7243C-0.0924926 15.3568 -0.0924926 14.7609 0.277478 14.3933L6.71285 8L0.277478 1.60669C-0.0924926 1.23914 -0.0924926 0.643215 0.277478 0.275663C0.647448 -0.0918894 1.24729 -0.0918894 1.61726 0.275663L8.72252 7.33449C9.09249 7.70204 9.09249 8.29796 8.72252 8.66551L1.61726 15.7243C1.24729 16.0919 0.647448 16.0919 0.277478 15.7243Z"
            fill="black"
          />
        </svg>
      </span>
    </div>
  );
}

export default async function AddProductDetailsPage({ searchParams }) {
  const resolvedSearchParams = await searchParams;
  const rootId = resolvedSearchParams?.root ?? '';
  const groupId = resolvedSearchParams?.group ?? '';
  const leafId = resolvedSearchParams?.leaf ?? '';

  const { root, group, leaf } = findProductCategoryPath(
    rootId,
    groupId,
    leafId,
  );
  const leafLabel = leaf?.label ?? 'Категория';

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <Link
          href="/admin/products/add"
          className={styles.backButton}
          aria-label="Назад к выбору категории"
        >
          <BackArrowIcon />
        </Link>
        <h1 className={styles.title}>Добавление товара</h1>
      </div>

      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          {/* Breadcrumbs */}
          <div className={styles.breadcrumbs}>
            <Crumb label={root?.label ?? 'Одежда, обувь и аксессуары'} />
            <Crumb label={group?.label ?? 'Категория'} />
            <Crumb label={leafLabel} />
          </div>

          <ProductDetailsForm leafLabel={leafLabel} />
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <section className={styles.previewCard}>
            <h2 className={styles.previewTitle}>Предпросмотр</h2>
            <div className={styles.previewPhone}>
              <div className={styles.previewScreen}>
                <div className={styles.previewImage}>
                  <span className={styles.previewHeart}>
                    <svg
                      width="30"
                      height="27"
                      viewBox="0 0 30 27"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M14.7174 6.0979C11.7802 -0.74505 1.5 -0.0162138 1.5 8.72986C1.5 17.4759 14.7174 24.7645 14.7174 24.7645C14.7174 24.7645 27.9348 17.4759 27.9348 8.72986C27.9348 -0.0162138 17.6546 -0.74505 14.7174 6.0979Z"
                        fill="white"
                        stroke="#B6B6B6"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                </div>
                <div className={styles.previewMeta}>
                  <div className={styles.previewTextLine} />
                  <div className={styles.previewTextShort} />
                </div>
                <p className={styles.previewName}>{leafLabel}</p>
              </div>
            </div>
          </section>

          <div className={styles.actions}>
            <button type="button" className={styles.secondaryButton}>
              Сохранить черновик
            </button>
            <button type="button" className={styles.primaryButton}>
              Опубликовать
            </button>
          </div>
        </aside>
      </div>
    </section>
  );
}
