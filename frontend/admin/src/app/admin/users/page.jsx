'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pagination } from '@/components/ui/Pagination';
import { UserFilters } from '@/components/admin/users/UserFilters';
import { UserRow } from '@/components/admin/users/UserRow';
import { UserDetailModal } from '@/components/admin/users/UserDetailModal';
import styles from './page.module.css';

const PER_PAGE = 20;

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    search: '',
    roleId: '',
    isActive: '',
  });
  const [editUser, setEditUser] = useState(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      params.set('offset', String((page - 1) * PER_PAGE));
      params.set('limit', String(PER_PAGE));
      params.set('sortBy', 'created_at');
      params.set('sortOrder', 'desc');

      if (filters.search.trim()) {
        params.set('search', filters.search.trim());
      }
      if (filters.roleId) {
        params.set('roleId', filters.roleId);
      }
      if (filters.isActive !== '') {
        params.set('isActive', filters.isActive);
      }

      const res = await fetch(`/api/admin/identities?${params.toString()}`);
      if (!res.ok) {
        throw new Error('Не удалось загрузить пользователей');
      }
      const data = await res.json();

      setUsers(Array.isArray(data) ? data : data.items || []);
      setTotal(
        typeof data.total === 'number'
          ? data.total
          : Array.isArray(data)
            ? data.length
            : 0,
      );
    } catch {
      setError('Ошибка загрузки пользователей');
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  const fetchRoles = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/roles');
      if (res.ok) {
        const data = await res.json();
        setRoles(Array.isArray(data) ? data : data.items || []);
      }
    } catch {
      // silent — roles dropdown will be empty
    }
  }, []);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  function handleEdit(user) {
    setEditUser(user);
  }

  function handleModalClose() {
    setEditUser(null);
  }

  function handleModalUpdate() {
    fetchUsers();
  }

  return (
    <section className={styles.page}>
      <h1 className={styles.title}>Пользователи</h1>

      <UserFilters roles={roles} onFilterChange={handleFilterChange} />

      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.list}>
        {loading ? (
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
                onEdit={handleEdit}
              />
            ))}
          </>
        )}
      </div>

      {!loading && users.length > 0 && (
        <Pagination page={page} pages={pages} onPage={setPage} />
      )}

      <UserDetailModal
        identityId={editUser?.identityId || editUser?.id || null}
        open={Boolean(editUser)}
        onClose={handleModalClose}
        onUpdate={handleModalUpdate}
      />
    </section>
  );
}
