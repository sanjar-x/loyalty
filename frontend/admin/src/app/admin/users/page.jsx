'use client';

import { useCallback, useMemo, useState } from 'react';
import { Pagination } from '@/shared/ui/Pagination';
import { useRoles } from '@/entities/role';
import {
  UserDetailModal,
  UserFilters,
  UserRow,
  useIdentities,
} from '@/entities/user';
import styles from './page.module.css';

const PER_PAGE = 20;

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    search: '',
    roleId: '',
    isActive: '',
  });
  const [editUser, setEditUser] = useState(null);

  const {
    data: identitiesResponse,
    isPending: usersLoading,
    error: usersError,
  } = useIdentities({ ...filters, page, limit: PER_PAGE });

  const { data: roles = [] } = useRoles();

  const users = identitiesResponse?.items ?? [];
  const total = identitiesResponse?.total ?? 0;

  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Пользователи</h1>

      <UserFilters roles={roles} onFilterChange={handleFilterChange} />

      {usersError && (
        <div className={styles.errorBanner}>Ошибка загрузки пользователей</div>
      )}

      <div className={styles.list}>
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
          <>
            <div className={styles.tableHeader}>
              <span className={styles.headerCell}>Email</span>
              <span className={styles.headerCell}>Имя</span>
              <span className={styles.headerCell}>Роли</span>
              <span className={styles.headerCell}>Статус</span>
              <span className={styles.headerCell} />
            </div>
            {users.map((user) => (
              <UserRow
                key={user.identityId || user.id}
                user={user}
                onEdit={setEditUser}
              />
            ))}
          </>
        )}
      </div>

      {!usersLoading && users.length > 0 && (
        <Pagination page={page} pages={pages} onPage={setPage} />
      )}

      <UserDetailModal
        identityId={editUser?.identityId || editUser?.id || null}
        open={Boolean(editUser)}
        onClose={() => setEditUser(null)}
        // Mutations inside the modal already invalidate identities cache, so
        // there's nothing extra to do here. Keep the prop callable for future
        // analytics hooks.
        onUpdate={() => {}}
      />
    </section>
  );
}
