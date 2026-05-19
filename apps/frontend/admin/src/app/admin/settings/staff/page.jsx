'use client';

import {
  Suspense,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import { useRoles } from '@/entities/role';
import { PermissionsTab, RolesTab } from '@/features/role-management';
import {
  INVITATION_STATUSES,
  INVITATION_STATUS_LABELS,
  InvitationRow,
  InviteStaffModal,
  StaffDetailModal,
  StaffFilters,
  StaffRow,
  staffStyles,
  useResendInvitation,
  useRevokeInvitation,
  useStaffInvitations,
  useStaffList,
} from '@/entities/staff';

import { useToast } from '@/shared/hooks/useToast';
import { pluralizeRu } from '@/shared/lib/utils';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { Pagination } from '@/shared/ui/Pagination';

import styles from './page.module.css';

const PER_PAGE = 20;
const DEFAULT_STAFF_FILTERS = {
  search: '',
  roleId: '',
  isActive: '',
  sort: 'created_at:desc',
};

function isAnomalyRow(member) {
  return (
    Boolean(member?.accountTypeMismatch) ||
    member?.hasStaffMemberProfile === false
  );
}

function StaffTab({ onTotal, deepLinkEmail, onDeepLinkConsumed }) {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState(DEFAULT_STAFF_FILTERS);
  const [openMember, setOpenMember] = useState(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  // Client-side filter only — backend has no anomaly query param yet (see
  // future ticket "anomaly filter on backend"). Re-evaluating on the
  // current page is acceptable for now: anomalies are rare and the operator
  // can paginate to find more.
  const [anomaliesOnly, setAnomaliesOnly] = useState(false);

  // InvitationsTab passes `?staff=email@x` when the operator clicks "Открыть
  // профиль" on an ACCEPTED row — backend invitation DTO doesn't carry
  // identityId, so we deep-link by email instead. Apply once then clear the
  // signal so the operator can change filters without it being re-applied.
  useEffect(() => {
    if (!deepLinkEmail) return;
    setFilters((prev) => ({ ...prev, search: deepLinkEmail }));
    setPage(1);
    onDeepLinkConsumed?.();
  }, [deepLinkEmail, onDeepLinkConsumed]);

  const { data: roles = [] } = useRoles();
  const { data, isPending, isFetching, error } = useStaffList({
    ...filters,
    page,
    limit: PER_PAGE,
  });

  // useMemo on `items` so the downstream `useMemo`s below get a stable
  // reference — the `??` fallback would otherwise allocate a fresh array
  // on every render and re-fire reducers/filters needlessly.
  const items = useMemo(() => data?.items ?? [], [data]);
  const total = data?.total ?? 0;
  const anomalyCount = useMemo(
    () => items.reduce((acc, m) => (isAnomalyRow(m) ? acc + 1 : acc), 0),
    [items],
  );
  const visibleItems = useMemo(
    () => (anomaliesOnly ? items.filter(isAnomalyRow) : items),
    [items, anomaliesOnly],
  );
  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );
  const moreOnOtherPages = total > items.length;

  useEffect(() => {
    if (typeof total === 'number') onTotal?.(total);
  }, [total, onTotal]);

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

  const showList = !isPending && visibleItems.length > 0;

  return (
    <>
      <div className={styles.toolbar}>
        <div className={styles.toolbarFilters}>
          <span className={styles.toolbarTotal}>
            {total > 0
              ? `${total.toLocaleString('ru-RU')} ${pluralizeRu(total, 'сотрудник', 'сотрудника', 'сотрудников')}`
              : ''}
          </span>
          {anomalyCount > 0 && (
            <span className={staffStyles.summaryAnomalies}>
              · С аномалиями: {anomalyCount}
              {moreOnOtherPages && (
                <span className={staffStyles.summaryAnomaliesHint}>
                  {' '}
                  (на этой странице)
                </span>
              )}
            </span>
          )}
        </div>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setInviteOpen(true)}
        >
          + Пригласить сотрудника
        </button>
      </div>

      <div className={staffStyles.filtersRow}>
        <StaffFilters
          value={filters}
          roles={roles}
          onFilterChange={handleFilterChange}
        />
        <label
          className={`${staffStyles.anomalyToggle} ${
            anomaliesOnly ? staffStyles.anomalyToggleActive : ''
          }`}
        >
          <input
            type="checkbox"
            checked={anomaliesOnly}
            onChange={(e) => setAnomaliesOnly(e.target.checked)}
          />
          <span>
            Только аномалии
            {anomaliesOnly && moreOnOtherPages && (
              <span className={staffStyles.anomalyToggleHint}>
                {' '}
                (на этой странице)
              </span>
            )}
          </span>
          {anomalyCount > 0 && (
            <span className={staffStyles.anomalyToggleCount}>
              {anomalyCount}
            </span>
          )}
        </label>
      </div>

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
        ) : visibleItems.length === 0 ? (
          <div className={staffStyles.emptyState}>
            <p className={staffStyles.emptyTitle}>
              {anomaliesOnly && items.length > 0
                ? 'На этой странице нет аномалий'
                : 'Сотрудники не найдены'}
            </p>
            <p className={staffStyles.emptyDescription}>
              {anomaliesOnly && items.length > 0
                ? 'Перейдите на другую страницу или снимите фильтр'
                : 'Пригласите первого сотрудника или измените фильтры'}
            </p>
            {!anomaliesOnly && (
              <button
                type="button"
                onClick={() => setInviteOpen(true)}
                className={staffStyles.emptyCta}
              >
                + Пригласить сотрудника
              </button>
            )}
          </div>
        ) : (
          <>
            <div className={staffStyles.listHeader}>
              <span>Сотрудник</span>
              <span>Должность</span>
              <span>Роли</span>
              <span>Статус</span>
              <span>Добавлен</span>
            </div>
            <div className={staffStyles.list}>
              {visibleItems.map((member) => (
                <StaffRow
                  key={member.identityId}
                  member={member}
                  onOpen={setOpenMember}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {/* Pagination stays visible even with `anomaliesOnly` so the operator
          can move between pages to find more anomalies (the client-side
          filter only sees the current page). */}
      {showList && pages > 1 && (
        <div className={styles.pagination}>
          <Pagination page={page} pages={pages} onPage={setPage} />
        </div>
      )}

      <StaffDetailModal
        identityId={openMember?.identityId ?? null}
        listMember={openMember}
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

// Status filter buttons rendered as pill tabs (replaces the old <select>
// per the spec). "" = no filter / all statuses.
const STATUS_FILTERS = [
  { value: '', label: 'Все' },
  ...INVITATION_STATUSES.map((s) => ({
    value: s,
    label: INVITATION_STATUS_LABELS[s],
  })),
];

// Resend confirmation copy branches by status. PENDING is the only state
// with an "old link" — for REVOKED/EXPIRED the original is already dead
// and saying "old link will stop working" would be misleading.
function resendCopy(invitation) {
  if (invitation.status === 'PENDING') {
    return {
      title: 'Переотправить приглашение?',
      description: `Старая ссылка перестанет работать. Будет создана новая для ${invitation.email}.`,
      confirmLabel: 'Переотправить',
    };
  }
  return {
    title: 'Создать новое приглашение?',
    description: `Для ${invitation.email} будет создано новое приглашение и отправлена новая ссылка.`,
    confirmLabel: 'Создать',
  };
}

function InvitationsTab({ onTotal, onOpenStaffByEmail }) {
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [inviteOpen, setInviteOpen] = useState(false);
  // `resendResult` reuses InviteStaffModal's success-state for the
  // freshly-resent invitation — same copy-link UX as a fresh create.
  const [resendResult, setResendResult] = useState(null);
  // Track each in-flight mutation separately. `mutation.variables` only
  // keeps the *most recent* call's args, so two parallel calls would lose
  // the older spinner and re-enable its button mid-flight.
  const [revokingIds, setRevokingIds] = useState(() => new Set());
  const [resendingIds, setResendingIds] = useState(() => new Set());
  const [confirmState, setConfirmState] = useState(null);

  const toast = useToast();

  const { data, isPending, isFetching, error } = useStaffInvitations({
    status: status || undefined,
    page,
    limit: PER_PAGE,
  });

  const revokeMutation = useRevokeInvitation();
  const resendMutation = useResendInvitation();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = useMemo(
    () => Math.max(1, Math.ceil(total / PER_PAGE)),
    [total],
  );

  useEffect(() => {
    if (typeof total === 'number') onTotal?.(total);
  }, [total, onTotal]);

  function performRevoke(invitation) {
    setRevokingIds((prev) => {
      const next = new Set(prev);
      next.add(invitation.id);
      return next;
    });
    revokeMutation.mutate(invitation.id, {
      onSuccess: () => {
        toast.success(`Приглашение для ${invitation.email} отозвано`);
      },
      onError: (err) => {
        toast.error(err?.message ?? 'Не удалось отозвать приглашение');
      },
      onSettled: () => {
        setRevokingIds((prev) => {
          const next = new Set(prev);
          next.delete(invitation.id);
          return next;
        });
      },
    });
  }

  function performResend(invitation) {
    setResendingIds((prev) => {
      const next = new Set(prev);
      next.add(invitation.id);
      return next;
    });
    resendMutation.mutate(invitation.id, {
      onSuccess: (data) => {
        // Reuse InviteStaffModal's success-state to show the new link +
        // copy button. The list itself is invalidated by useResendInvitation.
        setResendResult(data);
      },
      onError: (err) => {
        toast.error(err?.message ?? 'Не удалось переотправить приглашение');
      },
      onSettled: () => {
        setResendingIds((prev) => {
          const next = new Set(prev);
          next.delete(invitation.id);
          return next;
        });
      },
    });
  }

  function handleRevoke(invitation) {
    setConfirmState({
      kind: 'revoke',
      invitation,
      title: 'Отозвать приглашение?',
      description: `Ссылка для ${invitation.email} перестанет работать. Это действие нельзя отменить.`,
      confirmLabel: 'Отозвать',
    });
  }

  function handleResend(invitation) {
    setConfirmState({
      kind: 'resend',
      invitation,
      ...resendCopy(invitation),
    });
  }

  function handleConfirm() {
    if (!confirmState) return;
    const { kind, invitation } = confirmState;
    setConfirmState(null);
    if (kind === 'revoke') performRevoke(invitation);
    else if (kind === 'resend') performResend(invitation);
  }

  return (
    <>
      <div className={styles.toolbar}>
        <div className={styles.toolbarFilters}>
          <div
            className={staffStyles.statusFilterTabs}
            role="group"
            aria-label="Фильтр по статусу приглашения"
          >
            {STATUS_FILTERS.map((s) => {
              const active = status === s.value;
              return (
                <button
                  key={s.value || 'all'}
                  type="button"
                  onClick={() => {
                    setStatus(s.value);
                    setPage(1);
                  }}
                  className={`${staffStyles.statusFilterTab} ${active ? staffStyles.statusFilterTabActive : ''}`}
                  aria-pressed={active}
                >
                  {s.label}
                </button>
              );
            })}
          </div>
          <span className={styles.toolbarTotal}>
            {total > 0
              ? `${total.toLocaleString('ru-RU')} ${pluralizeRu(total, 'приглашение', 'приглашения', 'приглашений')}`
              : ''}
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
            <p className={staffStyles.emptyTitle}>Пока нет приглашений</p>
            <p className={staffStyles.emptyDescription}>
              Пригласите первого сотрудника
            </p>
            <button
              type="button"
              onClick={() => setInviteOpen(true)}
              className={staffStyles.emptyCta}
            >
              + Пригласить сотрудника
            </button>
          </div>
        ) : (
          items.map((invitation) => (
            <InvitationRow
              key={invitation.id}
              invitation={invitation}
              onRevoke={handleRevoke}
              onResend={handleResend}
              onOpenProfile={() => onOpenStaffByEmail?.(invitation.email)}
              isRevoking={revokingIds.has(invitation.id)}
              isResending={resendingIds.has(invitation.id)}
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

      <InviteStaffModal
        open={Boolean(resendResult)}
        onClose={() => setResendResult(null)}
        initialInvitation={resendResult}
        title="Новая ссылка приглашения"
      />

      <ConfirmDialog
        open={Boolean(confirmState)}
        title={confirmState?.title ?? ''}
        description={confirmState?.description}
        confirmLabel={confirmState?.confirmLabel}
        variant={confirmState?.kind === 'revoke' ? 'danger' : 'neutral'}
        onConfirm={handleConfirm}
        onClose={() => setConfirmState(null)}
      />
    </>
  );
}

function RolesTabWithCount({ onTotal }) {
  const { data: roles } = useRoles();
  useEffect(() => {
    if (Array.isArray(roles)) onTotal?.(roles.length);
  }, [roles, onTotal]);
  return <RolesTab />;
}

const TABS = [
  { key: 'staff', label: 'Сотрудники' },
  { key: 'invitations', label: 'Приглашения' },
  { key: 'roles', label: 'Роли' },
  { key: 'permissions', label: 'Права' },
];

const TAB_KEYS = new Set(TABS.map((t) => t.key));

// Wrap in Suspense — `useSearchParams()` requires a Suspense boundary in
// Next.js 16 App Router for static prerendering to succeed. Without it,
// `next build` aborts with "Read more: nextjs.org/docs/messages/missing-suspense-with-csr-bailout".
export default function StaffPage() {
  return (
    <Suspense fallback={null}>
      <StaffPageInner />
    </Suspense>
  );
}

function StaffPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // ?tab=... is the URL source of truth — refresh, back-button, bookmarks
  // all work. Fall back to staff for missing/unknown values.
  const tabParam = searchParams.get('tab');
  const tab = TAB_KEYS.has(tabParam) ? tabParam : 'staff';
  const deepLinkStaffEmail = searchParams.get('staff') ?? null;

  const baseId = useId();
  const tabId = (key) => `${baseId}-tab-${key}`;
  const panelId = (key) => `${baseId}-panel-${key}`;
  const tabRefs = useRef({});

  // Counts shown next to tab labels. Children publish them via onTotal so
  // we don't issue duplicate API calls just for the badge — the counts
  // appear after each tab has been visited at least once.
  const [tabCounts, setTabCounts] = useState({
    staff: null,
    invitations: null,
    roles: null,
    permissions: null,
  });
  const setCount = useCallback(
    (key) => (n) =>
      setTabCounts((prev) => (prev[key] === n ? prev : { ...prev, [key]: n })),
    [],
  );

  const setTab = useCallback(
    (next) => {
      const params = new URLSearchParams(searchParams.toString());
      if (next === 'staff') params.delete('tab');
      else params.set('tab', next);
      // Clear ephemeral deep-link arg whenever tab changes — it's a one-shot
      // signal, not persistent filter state.
      if (next !== 'staff') params.delete('staff');
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : '?', { scroll: false });
    },
    [router, searchParams],
  );

  const clearStaffDeepLink = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    if (!params.has('staff')) return;
    params.delete('staff');
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : '?', { scroll: false });
  }, [router, searchParams]);

  const openStaffByEmail = useCallback(
    (email) => {
      if (!email) return;
      const params = new URLSearchParams(searchParams.toString());
      params.delete('tab');
      params.set('staff', email);
      router.replace(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

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
      <div
        role="tablist"
        aria-label="Разделы сотрудников"
        className={styles.tabs}
      >
        {TABS.map((t) => {
          const selected = tab === t.key;
          const count = tabCounts[t.key];
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
              {typeof count === 'number' && count > 0 && (
                <span className={styles.tabCount}>
                  {count.toLocaleString('ru-RU')}
                </span>
              )}
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
        {tab === 'staff' && (
          <StaffTab
            onTotal={setCount('staff')}
            deepLinkEmail={deepLinkStaffEmail}
            onDeepLinkConsumed={clearStaffDeepLink}
          />
        )}
      </div>
      <div
        role="tabpanel"
        id={panelId('invitations')}
        aria-labelledby={tabId('invitations')}
        hidden={tab !== 'invitations'}
      >
        {tab === 'invitations' && (
          <InvitationsTab
            onTotal={setCount('invitations')}
            onOpenStaffByEmail={openStaffByEmail}
          />
        )}
      </div>
      <div
        role="tabpanel"
        id={panelId('roles')}
        aria-labelledby={tabId('roles')}
        hidden={tab !== 'roles'}
      >
        {tab === 'roles' && <RolesTabWithCount onTotal={setCount('roles')} />}
      </div>
      <div
        role="tabpanel"
        id={panelId('permissions')}
        aria-labelledby={tabId('permissions')}
        hidden={tab !== 'permissions'}
      >
        {tab === 'permissions' && <PermissionsTab />}
      </div>
    </section>
  );
}
