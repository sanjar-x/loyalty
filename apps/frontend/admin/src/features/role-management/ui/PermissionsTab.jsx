'use client';

import { useCallback, useMemo, useRef, useState } from 'react';

import { usePermissions } from '@/entities/role';

// Russian labels for the canonical resource codenames; falls back to the raw
// resource string so a freshly-added backend resource still renders without
// a frontend release.
const RESOURCE_LABELS = {
  identity: 'Идентичности',
  staff: 'Сотрудники',
  customer: 'Клиенты',
  role: 'Роли',
  permission: 'Права',
  brand: 'Бренды',
  category: 'Категории',
  product: 'Товары',
  attribute: 'Атрибуты',
  order: 'Заказы',
  shipment: 'Доставка',
  pricing: 'Цены',
  media: 'Медиа',
};

const ACTION_LABELS = {
  read: 'Просмотр',
  create: 'Создание',
  update: 'Изменение',
  delete: 'Удаление',
  assign: 'Назначение',
  revoke: 'Отзыв',
  activate: 'Активация',
  deactivate: 'Деактивация',
  publish: 'Публикация',
  invite: 'Приглашение',
};

function resourceLabel(resource) {
  return RESOURCE_LABELS[resource] || resource;
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action;
}

export function PermissionsTab() {
  const { data: groups = [], isPending: loading, error } = usePermissions();
  const [query, setQuery] = useState('');
  // Map<resource, boolean> — explicit per-resource collapse. Default behavior:
  // when there are <=4 groups everything stays open (the operator can see
  // the whole catalog at once); above that we collapse-by-default so the
  // page doesn't scroll forever on first load.
  const [collapsed, setCollapsed] = useState(() => new Set());
  const sectionRefs = useRef({});

  const totalPermissions = useMemo(
    () =>
      groups.reduce(
        (acc, g) =>
          acc + (Array.isArray(g.permissions) ? g.permissions.length : 0),
        0,
      ),
    [groups],
  );

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((g) => ({
        ...g,
        permissions: (g.permissions || []).filter((p) => {
          // Search hay includes the localized resource AND action labels so
          // a russian-speaking operator can find «Просмотр» / «Сотрудники»
          // without having to know the raw codenames.
          const hay =
            `${p.codename} ${p.description ?? ''} ${resourceLabel(g.resource)} ${actionLabel(p.action)}`.toLowerCase();
          return hay.includes(q);
        }),
      }))
      .filter((g) => g.permissions.length > 0);
  }, [groups, query]);

  const toggleCollapsed = useCallback((resource) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(resource)) next.delete(resource);
      else next.add(resource);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => setCollapsed(new Set()), []);
  const collapseAll = useCallback(
    () => setCollapsed(new Set(groups.map((g) => g.resource))),
    [groups],
  );

  const scrollToResource = useCallback((resource) => {
    // Make sure the section is expanded before scrolling so the operator
    // actually sees content, not just the header.
    setCollapsed((prev) => {
      if (!prev.has(resource)) return prev;
      const next = new Set(prev);
      next.delete(resource);
      return next;
    });
    requestAnimationFrame(() => {
      sectionRefs.current[resource]?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  }, []);

  // Search auto-expands every matching group so the matches are visible
  // straight away — collapsing through a filter is rarely the intent.
  const searching = query.trim() !== '';

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-app-text text-sm font-semibold">
          {loading
            ? ''
            : `Всего прав: ${totalPermissions.toLocaleString('ru-RU')} в ${groups.length.toLocaleString('ru-RU')} группах`}
        </div>
        <div className="text-app-muted text-xs">
          Каталог прав — read-only. Создаются миграциями backend.
        </div>
      </div>

      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Поиск по codename, описанию, ресурсу или действию"
        className="text-app-text bg-app-card placeholder:text-app-text-secondary mb-3 h-11 w-full rounded-full border-0 px-4 text-sm font-medium outline-none focus:ring-2 focus:ring-[#4a90d9]/30"
      />

      {/* Resource chips — jump-to-anchor nav so the operator doesn't scroll
          through 80 rows to find «Сотрудники». Plus expand/collapse all
          when the list grows past what fits a screen. */}
      {!loading && groups.length > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={expandAll}
            className="text-app-muted hover:text-app-text text-xs font-semibold underline-offset-2 hover:underline"
          >
            Развернуть все
          </button>
          <span className="text-app-muted/40">·</span>
          <button
            type="button"
            onClick={collapseAll}
            className="text-app-muted hover:text-app-text text-xs font-semibold underline-offset-2 hover:underline"
          >
            Свернуть все
          </button>
          <span className="text-app-muted/30 mx-2">|</span>
          <div className="flex flex-wrap gap-1.5">
            {groups.map((g) => (
              <button
                key={g.resource}
                type="button"
                onClick={() => scrollToResource(g.resource)}
                className="border-app-border text-app-text hover:bg-app-card rounded-full border px-3 py-1 text-xs font-medium transition-colors"
              >
                {resourceLabel(g.resource)}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Не удалось загрузить права
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-app-card h-16 animate-pulse rounded-xl"
            />
          ))}
        </div>
      ) : filteredGroups.length === 0 ? (
        <div className="border-app-border flex flex-col items-center gap-2 rounded-2xl border border-dashed py-16 text-center">
          <p className="text-app-text text-base font-semibold">
            {query ? 'Ничего не найдено по запросу' : 'Каталог прав пуст'}
          </p>
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-app-muted hover:text-app-text text-sm underline"
            >
              Сбросить поиск
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filteredGroups.map((group) => {
            const isCollapsed = !searching && collapsed.has(group.resource);
            return (
              <section
                key={group.resource}
                ref={(el) => {
                  sectionRefs.current[group.resource] = el;
                }}
                className="border-app-border scroll-mt-4 overflow-hidden rounded-2xl border bg-white"
              >
                <button
                  type="button"
                  onClick={() => toggleCollapsed(group.resource)}
                  aria-expanded={!isCollapsed}
                  className="border-app-border hover:bg-app-card focus-visible:bg-app-card bg-app-bg-soft flex w-full items-baseline justify-between gap-3 border-b px-4 py-3 text-left transition-colors focus:outline-none"
                >
                  <div className="flex min-w-0 items-baseline gap-2">
                    <span
                      aria-hidden="true"
                      className={`text-app-muted text-xs transition-transform ${
                        isCollapsed ? '' : 'rotate-90'
                      }`}
                    >
                      ▶
                    </span>
                    <h3 className="text-app-text text-sm font-bold tracking-wide uppercase">
                      {resourceLabel(group.resource)}
                    </h3>
                    <code className="text-app-muted text-xs">
                      {group.resource}
                    </code>
                  </div>
                  <span className="text-app-muted text-xs tabular-nums">
                    {group.permissions.length}
                  </span>
                </button>
                {!isCollapsed && (
                  <ul className="divide-app-border divide-y">
                    {group.permissions.map((perm) => (
                      <li
                        key={perm.id}
                        className="grid grid-cols-[minmax(160px,1fr)_minmax(120px,0.6fr)_minmax(200px,2fr)] items-center gap-4 px-4 py-3"
                      >
                        <code className="text-app-text text-sm font-semibold tabular-nums">
                          {perm.codename}
                        </code>
                        <span className="text-app-muted text-xs">
                          {actionLabel(perm.action)}
                        </span>
                        <span className="text-app-muted text-sm">
                          {perm.description || '—'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
