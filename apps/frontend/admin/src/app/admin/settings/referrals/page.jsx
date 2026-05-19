'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import UsersIcon from '@/assets/icons/users.svg';
import BagIcon from '@/assets/icons/bag.svg';
import dayjs from '@/shared/lib/dayjs';
import { useBodyScrollLock } from '@/shared/hooks/useBodyScrollLock';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { getReferrals } from '@/entities/referral';
import { Pagination } from '@/shared/ui/Pagination';
import styles from './page.module.css';

const REFERRALS_PER_PAGE = 9;

export default function ReferralsPage() {
  const [page, setPage] = useState(1);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newLabel, setNewLabel] = useState('');
  const inputRef = useRef(null);

  const referrals = useMemo(() => getReferrals(), []);
  const pages = useMemo(
    () => Math.max(1, Math.ceil(referrals.length / REFERRALS_PER_PAGE)),
    [referrals.length],
  );
  const pageItems = useMemo(() => {
    const safePage = Math.min(page, pages);
    const start = (safePage - 1) * REFERRALS_PER_PAGE;
    return referrals.slice(start, start + REFERRALS_PER_PAGE);
  }, [page, pages, referrals]);

  const closeCreate = useCallback(() => {
    setIsCreateOpen(false);
    setNewLabel('');
  }, []);

  useBodyScrollLock(isCreateOpen);
  useEscapeKey(closeCreate, isCreateOpen);

  useEffect(() => {
    if (isCreateOpen) inputRef.current?.focus();
  }, [isCreateOpen]);

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.headerTitle}>Реферальные ссылки</h2>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setIsCreateOpen(true)}
        >
          Создать ссылку
        </button>
      </header>

      {isCreateOpen ? (
        <div
          className={styles.modalOverlay}
          role="presentation"
          onClick={closeCreate}
        >
          <div
            className={styles.modalCard}
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-referral-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3 id="create-referral-title" className={styles.modalTitle}>
                Создание ссылки
              </h3>
              <button
                type="button"
                className={styles.modalClose}
                onClick={closeCreate}
                aria-label="Закрыть"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M5 5L15 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                  <path
                    d="M15 5L5 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>

            <form
              className={styles.modalBody}
              onSubmit={(e) => {
                e.preventDefault();
                if (!newLabel.trim()) return;
                closeCreate();
              }}
            >
              <input
                ref={inputRef}
                className={styles.modalInput}
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                placeholder="Название"
              />

              <div className={styles.modalFooter}>
                <button
                  type="submit"
                  className={styles.modalSubmit}
                  disabled={!newLabel.trim()}
                >
                  Создать ссылку
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <div className={styles.table}>
        {pageItems.map((row) => (
          <div key={row.id} className={styles.row}>
            <div className={styles.cellName}>{row.label}</div>
            <div className={styles.cellDate}>
              {dayjs(row.createdAt).format('D MMMM HH:mm')}
            </div>
            <a
              className={styles.cellLink}
              href={row.url}
              target="_blank"
              rel="noreferrer"
            >
              {row.url}
            </a>

            <div className={styles.countCell}>
              <UsersIcon className={styles.countIcon} />
              <span className={styles.countValue}>
                {row.users.value.toLocaleString('ru-RU')}
                {row.users.delta > 0 ? (
                  <span className={styles.delta}>
                    +{row.users.delta.toLocaleString('ru-RU')}
                  </span>
                ) : null}
              </span>
            </div>

            <div className={styles.countCell}>
              <BagIcon className={styles.countIcon} />
              <span className={styles.countValue}>
                {row.orders.value.toLocaleString('ru-RU')}
                {row.orders.delta > 0 ? (
                  <span className={styles.delta}>
                    +{row.orders.delta.toLocaleString('ru-RU')}
                  </span>
                ) : null}
              </span>
            </div>

            <button
              type="button"
              className={styles.iconButton}
              aria-label="Статистика"
            >
              <svg
                className={styles.actionIcon}
                viewBox="0 0 26 26"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M16.25 24.6457H9.74996C3.86746 24.6457 1.35413 22.1323 1.35413 16.2498V9.74984C1.35413 3.86734 3.86746 1.354 9.74996 1.354H16.25C22.1325 1.354 24.6458 3.86734 24.6458 9.74984V16.2498C24.6458 22.1323 22.1325 24.6457 16.25 24.6457ZM9.74996 2.979C4.75579 2.979 2.97913 4.75567 2.97913 9.74984V16.2498C2.97913 21.244 4.75579 23.0207 9.74996 23.0207H16.25C21.2441 23.0207 23.0208 21.244 23.0208 16.2498V9.74984C23.0208 4.75567 21.2441 2.979 16.25 2.979H9.74996Z"
                  fill="#292D32"
                />
                <path
                  d="M7.94079 16.51C7.76746 16.51 7.59413 16.4558 7.44246 16.3367C7.08496 16.0658 7.01996 15.5567 7.29079 15.1992L9.86912 11.8517C10.1833 11.4508 10.6275 11.1908 11.1366 11.1258C11.635 11.0608 12.1441 11.2017 12.545 11.5158L14.5275 13.0758C14.6033 13.1408 14.6791 13.1408 14.7333 13.13C14.7766 13.13 14.8525 13.1083 14.9175 13.0217L17.42 9.79334C17.6908 9.43584 18.2108 9.37084 18.5575 9.65251C18.915 9.92334 18.98 10.4325 18.6983 10.79L16.1958 14.0183C15.8816 14.4192 15.4375 14.6792 14.9283 14.7333C14.4191 14.7983 13.9208 14.6575 13.52 14.3433L11.5375 12.7833C11.4616 12.7183 11.375 12.7183 11.3316 12.7292C11.2883 12.7292 11.2125 12.7508 11.1475 12.8375L8.56913 16.185C8.42829 16.4017 8.18996 16.51 7.94079 16.51Z"
                  fill="#292D32"
                />
              </svg>
            </button>
          </div>
        ))}
      </div>

      <Pagination page={page} pages={pages} onPage={setPage} />
    </section>
  );
}
