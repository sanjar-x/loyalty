'use client';

import { useMemo, useState } from 'react';
import clsx from 'clsx';
import { Trash2 } from 'lucide-react';

import Footer from '@/components/layout/Footer';
import Header from '@/components/layout/Header';
import BottomSheet from '@/components/ui/BottomSheet';

import styles from './page.module.css';

function Stars({ value = 0 }) {
  const rating = Math.max(0, Math.min(5, Math.floor(Number(value) || 0)));

  return (
    <div className={styles.stars} aria-label={`Рейтинг: ${rating} из 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <img
          key={index}
          src={index < rating ? '/icons/product/ratedStar.svg' : '/icons/product/Star.svg'}
          alt=""
          aria-hidden="true"
          className={clsx(styles.star, index < rating ? styles.starOn : styles.starOff)}
          loading="lazy"
        />
      ))}
    </div>
  );
}

const StarsClone = ({ rating }) => {
  return (
    <div style={{ display: 'flex', gap: '4px' }}>
      {[1, 2, 3, 4, 5].map((star) => (
        <svg
          key={star}
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill={star <= rating ? '#000000' : 'none'}
          stroke="#000000"
          strokeWidth="1.5"
        >
          <path d="M12 2l2.9 6.3 6.9.6-5.2 4.6 1.6 6.8L12 17.8 5.8 20.3l1.6-6.8L2.2 8.9l6.9-.6L12 2z" />
        </svg>
      ))}
    </div>
  );
};

function ReviewCard({ item, showMenu = false, onMenu }) {
  const hasReviewDetails = Boolean(
    item?.reviewedAt ||
    (item?.photos && item.photos.length) ||
    item?.pros ||
    item?.cons ||
    item?.comment
  );

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <div
          className={`${styles.thumbWrap} ${hasReviewDetails ? `${styles.thumbWrapSmall}` : ''}`}
        >
          <img src={item.image} alt={item.name} className={styles.thumb} loading="lazy" />
        </div>

        <div className={styles.cardWrapperRight}>
          <div className={styles.headerText}>
            <div className={styles.cardTitle}>{item.name}</div>
            <div className={styles.cardMeta}>
              <span>
                Размер: <span className={styles.blackSize}>{item.size}</span>
              </span>
              <span className={styles.dot}>·</span>
              <span>
                Артикул: <span className={styles.blackSize}>{item.article}</span>
              </span>
            </div>
          </div>

          {!hasReviewDetails ? (
            <div className={styles.reviewLine}>
              <Stars value={item.rating} />
              {item.reviewedAt ? (
                <div className={styles.reviewDate}>
                  <span className={styles.dot}>·</span>
                  <span>{item.reviewedAt}</span>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
        {showMenu ? (
          <button
            type="button"
            className={styles.menuBtn}
            aria-label="Меню"
            onClick={() => onMenu?.(item)}
          >
            ⋮
          </button>
        ) : null}
      </div>

      {hasReviewDetails ? (
        <div
          className={`${styles.reviewLine} ${hasReviewDetails ? `${styles.reviewLineSmall}` : ''}`}
        >
          <StarsClone rating={item.rating} />
          {item.reviewedAt ? (
            <div className={styles.reviewDate}>
              <span className={styles.dot}>·</span>
              <span>{item.reviewedAt}</span>
            </div>
          ) : null}
        </div>
      ) : null}

      {hasReviewDetails && item.photos?.length ? (
        <div className={styles.photos}>
          {item.photos.slice(0, 6).map((src, index) => (
            <img
              key={`${item.id}-photo-${index}`}
              src={src}
              alt=""
              aria-hidden="true"
              className={styles.photo}
              loading="lazy"
            />
          ))}
        </div>
      ) : null}

      {hasReviewDetails ? (
        <div className={styles.reviewText}>
          {item.pros ? (
            <div className={styles.reviewRow}>
              <span className={styles.reviewLabel}>Достоинства:</span> {item.pros}
            </div>
          ) : null}
          {item.cons ? (
            <div className={styles.reviewRow}>
              <span className={styles.reviewLabel}>Недостатки:</span> {item.cons}
            </div>
          ) : null}
          {item.comment ? (
            <div className={styles.reviewRow}>
              <span className={styles.reviewLabel}>Комментарий:</span> {item.comment}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function ReviewsPage() {
  const [tab, setTab] = useState('pending');
  const [isReviewMenuOpen, setIsReviewMenuOpen] = useState(false);
  const [activeReviewId, setActiveReviewId] = useState(null);

  // Backend Reviews moduli yo'q (Spec §11) — bo'sh boshlanish.
  // Modul tayyor bo'lganda `usePendingReviewsQuery` / `useMyReviewsQuery`'ga ulanadi.
  const pendingItems = useMemo(() => [], []);
  const [reviewedItems, setReviewedItems] = useState([]);

  const items = tab === 'pending' ? pendingItems : reviewedItems;

  const closeReviewMenu = () => {
    setIsReviewMenuOpen(false);
    setActiveReviewId(null);
  };

  const confirmDeleteReview = () => {
    if (!activeReviewId) return;
    setReviewedItems((prev) => prev.filter((r) => r.id !== activeReviewId));
    closeReviewMenu();
  };

  return (
    <div className={styles.page}>
      <Header title="Отзывы" />
      <header className={styles.header}>
        <div className={styles.tabs} role="tablist" aria-label="Отзывы">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'pending'}
            className={clsx(styles.tab, tab === 'pending' ? styles.tabActive : styles.tabInactive)}
            onClick={() => setTab('pending')}
          >
            Ждут отзыва
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'reviewed'}
            className={clsx(styles.tab, tab === 'reviewed' ? styles.tabActive : styles.tabInactive)}
            onClick={() => setTab('reviewed')}
          >
            Отзывы
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {items.length > 0 ? (
          <div className={styles.list}>
            {items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                showMenu={tab === 'reviewed'}
                onMenu={(it) => {
                  setActiveReviewId(it.id);
                  setIsReviewMenuOpen(true);
                }}
              />
            ))}
          </div>
        ) : (
          <section className={styles.emptyState} role="status" aria-live="polite">
            <div className={styles.emptyTitle}>
              {tab === 'pending' ? 'Нет товаров для отзыва' : 'Отзывов пока нет'}
            </div>
            <div className={styles.emptyText}>
              {tab === 'pending'
                ? 'После получения заказов товары появятся здесь'
                : 'Ваши отзывы будут отображаться здесь'}
            </div>
          </section>
        )}
      </main>

      <BottomSheet
        open={tab === 'reviewed' && isReviewMenuOpen}
        onClose={closeReviewMenu}
        ariaLabel="Действия с отзывом"
        header={<div className={styles.deleteSheetHeader} />}
        isReview={true}
      >
        <div className={styles.deleteSheetContent}>
          <button
            type="button"
            onClick={confirmDeleteReview}
            className={styles.deleteActionBtn}
            disabled={!activeReviewId}
          >
            <Trash2 className={styles.deleteActionIcon} />
            <span>Удалить отзыв</span>
          </button>

          <button type="button" onClick={closeReviewMenu} className={styles.deleteCancelBtn}>
            Отмена
          </button>
        </div>
      </BottomSheet>

      <Footer />
    </div>
  );
}
