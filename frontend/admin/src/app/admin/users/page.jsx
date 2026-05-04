'use client';

import { useCallback, useMemo, useState } from 'react';

import {
  UserDetailModal,
  UserFilters,
  UserMetrics,
  UserRow,
  useCustomers,
} from '@/entities/user';

import { Pagination } from '@/shared/ui/Pagination';

import styles from './page.module.css';

const PER_PAGE = 20;
const DEFAULT_SORT = 'created_at:desc';
const INITIAL_FILTERS = { search: '', sort: DEFAULT_SORT };

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [editUser, setEditUser] = useState(null);

  const {
    data: customersResponse,
    isPending: usersLoading,
    isFetching,
    error: usersError,
  } = useCustomers({ ...filters, page, limit: PER_PAGE });

  const users = customersResponse?.items ?? [];
  const total = customersResponse?.total ?? 0;

  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  const handleFilterChange = useCallback((newFilters) => {
    setFilters((prev) => {
      const next = { ...prev, ...newFilters };
      if (next.search !== prev.search || next.sort !== prev.sort) {
        // Reset pagination only when the underlying query actually changed.
        setPage(1);
      }
      return next;
    });
  }, []);

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Пользователи</h1>

      <UserMetrics users={users} total={total} />

      <UserFilters value={filters} onFilterChange={handleFilterChange} />

      {usersError && (
        <div className={styles.errorBanner}>Ошибка загрузки пользователей</div>
      )}

      <div className={styles.list} aria-busy={isFetching || usersLoading}>
        {usersLoading ? (
          <div className={styles.skeleton}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className={styles.skeletonRow} />
            ))}
          </div>
        ) : users.length === 0 ? (
          <div className={styles.emptyState}>
            <p className={styles.emptyTitle}>Пользователи не найдены</p>
            <p className={styles.emptyDescription}>
              Попробуйте изменить параметры поиска
            </p>
          </div>
        ) : (
          users.map((user) => (
            <UserRow key={user.identityId} user={user} onEdit={setEditUser} />
          ))
        )}
      </div>

      {!usersLoading && users.length > 0 && pages > 1 && (
        <div className={styles.pagination}>
          <Pagination page={page} pages={pages} onPage={setPage} />
        </div>
      )}

      <UserDetailModal
        identityId={editUser?.identityId ?? null}
        open={Boolean(editUser)}
        onClose={() => setEditUser(null)}
        // Mutations inside the modal already invalidate customers cache.
        onUpdate={() => {}}
      />
    </section>
  );
}
