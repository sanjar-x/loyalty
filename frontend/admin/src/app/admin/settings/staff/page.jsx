'use client';

import { useCallback, useId, useMemo, useRef, useState } from 'react';

import { useRoles } from '@/entities/role';
import {
  INVITATION_STATUSES,
  INVITATION_STATUS_LABELS,
  InvitationRow,
  InviteStaffModal,
  StaffDetailModal,
  StaffFilters,
  StaffRow,
  staffStyles,
  useRevokeInvitation,
  useStaffInvitations,
  useStaffList,
} from '@/entities/staff';

import { Pagination } from '@/shared/ui/Pagination';

import styles from './page.module.css';

const PER_PAGE = 20;
const DEFAULT_STAFF_FILTERS = {
  search: '',
  roleId: '',
  isActive: '',
  sort: 'created_at:desc',
};

function StaffTab() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(DEFAULT_STAFF_FILTERS);
  const [openMember, setOpenMember] = useState(null);
  const [inviteOpen, setInviteOpen] = useState(false);

  const { data: roles = [] } = useRoles();
  const { data, isPending, isFetching, error } = useStaffList({
    ...filters,
    page,
    limit: PER_PAGE,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  const handleFilterChange = useCallback((next) => {
    setFilters((prev) => {
      const merged = { ...prev, ...next };
      if (
        merged.search !== prev.search ||
        merged.roleId !== prev.roleId ||
        merged.isActive !== prev.isActive ||
        merged.sort !== prev.sort
      ) {
        setPage(1);
      }
      return merged;
    });
  }, []);

  return (
    <>
      <div className={styles.toolbar}>
        <span className={styles.toolbarTotal}>
          {total > 0 ? `${total.toLocaleString('ru-RU')} сотрудников` : ''}
        </span>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setInviteOpen(true)}
        >
          + Пригласить сотрудника
        </button>
      </div>

      <StaffFilters
        value={filters}
        roles={roles}
        onFilterChange={handleFilterChange}
      />

      {error && (
        <div className={staffStyles.modalError}>
          Ошибка загрузки сотрудников
        </div>
      )}

      <div aria-busy={isFetching || isPending}>
        {isPending ? (
          <div className={staffStyles.skeleton}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={staffStyles.skeletonRow} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className={staffStyles.emptyState}>
            <p className={staffStyles.emptyTitle}>Сотрудники не найдены</p>
            <p className={staffStyles.emptyDescription}>
              Пригласите первого сотрудника или измените фильтры
            </p>
          </div>
        ) : (
          items.map((member) => (
            <StaffRow
              key={member.identityId}
              member={member}
              onOpen={setOpenMember}
            />
          ))
        )}
      </div>

      {!isPending && items.length > 0 && pages > 1 && (
        <div className={styles.pagination}>
          <Pagination page={page} pages={pages} onPage={setPage} />
        </div>
      )}

      <StaffDetailModal
        identityId={openMember?.identityId ?? null}
        open={Boolean(openMember)}
        onClose={() => setOpenMember(null)}
        onUpdate={() => {}}
      />

      <InviteStaffModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onCreated={() => {}}
      />
    </>
  );
}

function InvitationsTab() {
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [inviteOpen, setInviteOpen] = useState(false);
  // Track each in-flight revoke separately. `mutation.variables` only keeps
  // the *most recent* call's args, so two parallel revokes would lose the
  // older spinner and re-enable its button mid-flight.
  const [revokingIds, setRevokingIds] = useState(() => new Set());

  const { data, isPending, isFetching, error } = useStaffInvitations({
    status: status || undefined,
    page,
    limit: PER_PAGE,
  });

  const revokeMutation = useRevokeInvitation();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  function handleRevoke(invitation) {
    if (!confirm(`Отозвать приглашение для ${invitation.email}?`)) return;
    setRevokingIds((prev) => {
      const next = new Set(prev);
      next.add(invitation.id);
      return next;
    });
    revokeMutation.mutate(invitation.id, {
      onSettled: () => {
        setRevokingIds((prev) => {
          const next = new Set(prev);
          next.delete(invitation.id);
          return next;
        });
      },
    });
  }

  return (
    <>
      <div className={styles.toolbar}>
        <div className={styles.toolbarFilters}>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className={staffStyles.filterSelect}
            aria-label="Фильтр по статусу приглашения"
          >
            <option value="">Все статусы</option>
            {INVITATION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {INVITATION_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
          <span className={styles.toolbarTotal}>
            {total > 0 ? `${total.toLocaleString('ru-RU')} приглашений` : ''}
          </span>
        </div>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setInviteOpen(true)}
        >
          + Пригласить сотрудника
        </button>
      </div>

      {error && (
        <div className={staffStyles.modalError}>
          Ошибка загрузки приглашений
        </div>
      )}

      <div aria-busy={isFetching || isPending}>
        {isPending ? (
          <div className={staffStyles.skeleton}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={staffStyles.skeletonRow} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className={staffStyles.emptyState}>
            <p className={staffStyles.emptyTitle}>Приглашений нет</p>
            <p className={staffStyles.emptyDescription}>
              Создайте новое приглашение для добавления сотрудника
            </p>
          </div>
        ) : (
          items.map((invitation) => (
            <InvitationRow
              key={invitation.id}
              invitation={invitation}
              onRevoke={handleRevoke}
              isRevoking={revokingIds.has(invitation.id)}
            />
          ))
        )}
      </div>

      {!isPending && items.length > 0 && pages > 1 && (
        <div className={styles.pagination}>
          <Pagination page={page} pages={pages} onPage={setPage} />
        </div>
      )}

      <InviteStaffModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        onCreated={() => {}}
      />
    </>
  );
}

const TABS = [
  { key: 'staff', label: 'Сотрудники' },
  { key: 'invitations', label: 'Приглашения' },
];

export default function StaffPage() {
  const [tab, setTab] = useState('staff');
  const baseId = useId();
  const tabId = (key) => `${baseId}-tab-${key}`;
  const panelId = (key) => `${baseId}-panel-${key}`;
  const tabRefs = useRef({});

  // Roving tab keyboard navigation per WAI-ARIA APG. Left/Right cycles tabs;
  // Home/End jump to first/last. Without this, the `role="tab"` hint to
  // screen readers is misleading because the panel relationship is wired up
  // (`aria-controls` / `aria-labelledby`) but arrow nav isn't.
  function handleTabKeyDown(e) {
    const idx = TABS.findIndex((t) => t.key === tab);
    if (idx < 0) return;
    let nextIdx = null;
    if (e.key === 'ArrowRight') nextIdx = (idx + 1) % TABS.length;
    else if (e.key === 'ArrowLeft')
      nextIdx = (idx - 1 + TABS.length) % TABS.length;
    else if (e.key === 'Home') nextIdx = 0;
    else if (e.key === 'End') nextIdx = TABS.length - 1;
    if (nextIdx === null) return;
    e.preventDefault();
    const nextKey = TABS[nextIdx].key;
    setTab(nextKey);
    tabRefs.current[nextKey]?.focus();
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Сотрудники</h1>
      </header>

      <div
        role="tablist"
        aria-label="Разделы сотрудников"
        className={styles.tabs}
      >
        {TABS.map((t) => {
          const selected = tab === t.key;
          return (
            <button
              key={t.key}
              ref={(el) => {
                tabRefs.current[t.key] = el;
              }}
              type="button"
              role="tab"
              id={tabId(t.key)}
              aria-selected={selected}
              aria-controls={panelId(t.key)}
              tabIndex={selected ? 0 : -1}
              className={`${styles.tab} ${selected ? styles.tabActive : ''}`}
              onClick={() => setTab(t.key)}
              onKeyDown={handleTabKeyDown}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={panelId('staff')}
        aria-labelledby={tabId('staff')}
        hidden={tab !== 'staff'}
      >
        {tab === 'staff' && <StaffTab />}
      </div>
      <div
        role="tabpanel"
        id={panelId('invitations')}
        aria-labelledby={tabId('invitations')}
        hidden={tab !== 'invitations'}
      >
        {tab === 'invitations' && <InvitationsTab />}
      </div>
    </section>
  );
}
