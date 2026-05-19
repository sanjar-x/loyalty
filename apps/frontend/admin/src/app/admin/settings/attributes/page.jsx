'use client';

import { useId, useMemo, useRef, useState } from 'react';

import { AttributeRow, useAttributes } from '@/entities/attribute';
import {
  AttributeGroupRow,
  useAttributeGroups,
  useDeleteAttributeGroup,
} from '@/entities/attribute-group';
import {
  AttributeValueRow,
  useActivateAttributeValue,
  useAttributeValues,
  useDeactivateAttributeValue,
  useDeleteAttributeValue,
} from '@/entities/attribute-value';
import {
  AttributeFormModal,
  AttributeGroupFormModal,
  AttributeValueFormModal,
  BulkAttributeValuesModal,
  DeleteAttributeConfirmModal,
} from '@/features/attribute-form';

import { i18n } from '@/shared/lib/utils';

const TABS = [
  { key: 'attributes', label: 'Атрибуты' },
  { key: 'groups', label: 'Группы' },
  { key: 'values', label: 'Значения' },
];

export default function AttributesAdminPage() {
  const [tab, setTab] = useState('attributes');
  const baseId = useId();
  const tabId = (key) => `${baseId}-tab-${key}`;
  const panelId = (key) => `${baseId}-panel-${key}`;
  const tabRefs = useRef({});

  function handleTabKeyDown(event) {
    const idx = TABS.findIndex((t) => t.key === tab);
    if (idx < 0) return;
    let next = null;
    if (event.key === 'ArrowRight') next = (idx + 1) % TABS.length;
    else if (event.key === 'ArrowLeft')
      next = (idx - 1 + TABS.length) % TABS.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = TABS.length - 1;
    if (next === null) return;
    event.preventDefault();
    const nextKey = TABS[next].key;
    setTab(nextKey);
    tabRefs.current[nextKey]?.focus();
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-app-text text-xl font-semibold">Атрибуты</h2>
      </div>

      <div
        role="tablist"
        aria-label="Разделы атрибутов"
        className="border-app-border mb-5 flex gap-1 border-b"
      >
        {TABS.map((t) => {
          const selected = tab === t.key;
          return (
            <button
              key={t.key}
              role="tab"
              ref={(el) => {
                tabRefs.current[t.key] = el;
              }}
              type="button"
              id={tabId(t.key)}
              aria-selected={selected}
              aria-controls={panelId(t.key)}
              tabIndex={selected ? 0 : -1}
              onClick={() => setTab(t.key)}
              onKeyDown={handleTabKeyDown}
              className={`-mb-px rounded-t-lg px-4 py-2 text-sm font-medium transition-colors ${
                selected
                  ? 'border-app-text-dark text-app-text-dark border-b-2'
                  : 'text-app-muted hover:text-app-text-dark'
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={panelId('attributes')}
        aria-labelledby={tabId('attributes')}
        hidden={tab !== 'attributes'}
      >
        {tab === 'attributes' && <AttributesTab />}
      </div>
      <div
        role="tabpanel"
        id={panelId('groups')}
        aria-labelledby={tabId('groups')}
        hidden={tab !== 'groups'}
      >
        {tab === 'groups' && <GroupsTab />}
      </div>
      <div
        role="tabpanel"
        id={panelId('values')}
        aria-labelledby={tabId('values')}
        hidden={tab !== 'values'}
      >
        {tab === 'values' && <ValuesTab />}
      </div>
    </div>
  );
}

// ─── Attributes tab ──────────────────────────────────────────────────────────

function AttributesTab() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const { data, isPending, error } = useAttributes({ limit: 200 });

  const items = data?.items ?? [];

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-app-muted text-sm">
          {items.length > 0 && `Всего: ${items.length}`}
        </p>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white"
        >
          + Создать атрибут
        </button>
      </div>

      {error ? (
        <Panel error={error.message ?? 'Не удалось загрузить атрибуты'} />
      ) : isPending ? (
        <Skeleton />
      ) : items.length === 0 ? (
        <Empty
          title="Атрибутов ещё нет"
          action="Создать первый"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-app-border bg-app-card border-b">
                <Th>Атрибут</Th>
                <Th>Уровень / тип</Th>
                <Th>Признаки</Th>
                <Th align="right">Действия</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((attribute) => (
                <AttributeRow
                  key={attribute.id}
                  attribute={attribute}
                  onEdit={setEditTarget}
                  onDelete={setDeleteTarget}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AttributeFormModal
        open={createOpen}
        mode="create"
        onClose={() => setCreateOpen(false)}
      />
      <AttributeFormModal
        open={Boolean(editTarget)}
        mode="edit"
        attribute={editTarget}
        onClose={() => setEditTarget(null)}
      />
      <DeleteAttributeConfirmModal
        open={Boolean(deleteTarget)}
        attribute={deleteTarget}
        onClose={() => setDeleteTarget(null)}
      />
    </>
  );
}

// ─── Groups tab ──────────────────────────────────────────────────────────────

function GroupsTab() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const { data, isPending, error } = useAttributeGroups({ limit: 200 });
  const deleteMutation = useDeleteAttributeGroup();

  const groups = data?.items ?? [];

  function handleDelete(group) {
    if (!confirm(`Удалить группу «${i18n(group.nameI18N, group.code)}»?`)) {
      return;
    }
    deleteMutation.mutate(group.id);
  }

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-app-muted text-sm">
          {groups.length > 0 && `Всего: ${groups.length}`}
        </p>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white"
        >
          + Создать группу
        </button>
      </div>

      {error ? (
        <Panel error={error.message ?? 'Не удалось загрузить группы'} />
      ) : isPending ? (
        <Skeleton />
      ) : groups.length === 0 ? (
        <Empty
          title="Групп ещё нет"
          action="Создать первую"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-app-border bg-app-card border-b">
                <Th>Группа</Th>
                <Th>Порядок</Th>
                <Th align="right">Действия</Th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <AttributeGroupRow
                  key={group.id}
                  group={group}
                  onEdit={setEditTarget}
                  onDelete={handleDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AttributeGroupFormModal
        open={createOpen}
        mode="create"
        onClose={() => setCreateOpen(false)}
      />
      <AttributeGroupFormModal
        open={Boolean(editTarget)}
        mode="edit"
        group={editTarget}
        onClose={() => setEditTarget(null)}
      />
    </>
  );
}

// ─── Values tab ──────────────────────────────────────────────────────────────

function ValuesTab() {
  const attributesQuery = useAttributes({ isDictionary: true, limit: 200 });
  const dictionaryAttrs = useMemo(
    () => (attributesQuery.data?.items ?? []).filter((a) => a.isDictionary),
    [attributesQuery.data],
  );
  const [selectedAttrId, setSelectedAttrId] = useState('');

  // Auto-select the first dictionary attribute the first time the list
  // arrives so the table is never blank for an admin who just opened
  // the tab.
  if (!selectedAttrId && dictionaryAttrs.length > 0) {
    setSelectedAttrId(dictionaryAttrs[0].id);
  }

  return (
    <>
      <label className="mb-3 flex flex-col gap-1 text-sm sm:max-w-md">
        <span className="text-app-text-dark text-xs font-medium">Атрибут</span>
        <select
          value={selectedAttrId}
          onChange={(event) => setSelectedAttrId(event.target.value)}
          disabled={attributesQuery.isPending && !attributesQuery.data}
          className="border-app-border focus:border-app-text-dark rounded-lg border bg-white px-3 py-2 text-sm outline-none"
        >
          {attributesQuery.isPending && !attributesQuery.data && (
            <option value="">Загружаем…</option>
          )}
          {!attributesQuery.isPending && dictionaryAttrs.length === 0 && (
            <option value="">Нет справочных атрибутов</option>
          )}
          {dictionaryAttrs.map((attr) => (
            <option key={attr.id} value={attr.id}>
              {i18n(attr.nameI18N, attr.code)}
            </option>
          ))}
        </select>
      </label>

      {selectedAttrId ? (
        <ValuesPanel attributeId={selectedAttrId} />
      ) : (
        <Empty
          title="Сначала выберите справочный атрибут"
          subtitle="Значения создаются для атрибутов с включённым флагом «Справочник»."
        />
      )}
    </>
  );
}

function ValuesPanel({ attributeId }) {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [bulkOpen, setBulkOpen] = useState(false);

  const { data, isPending, error } = useAttributeValues(attributeId, {
    limit: 500,
  });
  const deactivateMutation = useDeactivateAttributeValue(attributeId);
  const activateMutation = useActivateAttributeValue(attributeId);
  const deleteMutation = useDeleteAttributeValue(attributeId);

  const items = data?.items ?? [];

  function handleToggle(value) {
    if (value.isActive) {
      deactivateMutation.mutate(value.id);
    } else {
      activateMutation.mutate(value.id);
    }
  }

  function handleDelete(value) {
    if (
      !confirm(
        `Удалить значение «${i18n(value.valueI18N, value.code)}»? Если значение используется SKU, backend вернёт 422 — деактивируйте вместо удаления.`,
      )
    ) {
      return;
    }
    deleteMutation.mutate(value.id);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-app-muted text-sm">
          {items.length > 0 && `Всего: ${items.length}`}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setBulkOpen(true)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-lg border px-3 py-2 text-sm font-medium"
          >
            Массовый ввод
          </button>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white"
          >
            + Создать значение
          </button>
        </div>
      </div>

      {error ? (
        <Panel error={error.message ?? 'Не удалось загрузить значения'} />
      ) : isPending ? (
        <Skeleton />
      ) : items.length === 0 ? (
        <Empty
          title="Значений ещё нет"
          action="Создать первое"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-app-border bg-app-card border-b">
                <Th>Значение</Th>
                <Th>Группа</Th>
                <Th>Порядок</Th>
                <Th>Состояние</Th>
                <Th align="right">Действия</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((value) => (
                <AttributeValueRow
                  key={value.id}
                  value={value}
                  onEdit={setEditTarget}
                  onToggleActive={handleToggle}
                  onDelete={handleDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AttributeValueFormModal
        open={createOpen}
        mode="create"
        attributeId={attributeId}
        onClose={() => setCreateOpen(false)}
      />
      <AttributeValueFormModal
        open={Boolean(editTarget)}
        mode="edit"
        attributeId={attributeId}
        value={editTarget}
        onClose={() => setEditTarget(null)}
      />
      <BulkAttributeValuesModal
        open={bulkOpen}
        attributeId={attributeId}
        onClose={() => setBulkOpen(false)}
      />
    </div>
  );
}

// ─── Shared bits ─────────────────────────────────────────────────────────────

function Th({ children, align = 'left' }) {
  return (
    <th
      className={`text-app-muted px-4 py-3 font-medium ${align === 'right' ? 'text-right' : ''}`}
    >
      {children}
    </th>
  );
}

function Skeleton() {
  return (
    <div className="border-app-border rounded-xl border p-6">
      <div className="bg-app-card h-6 w-1/3 animate-pulse rounded" />
      <div className="mt-4 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-app-card h-12 w-full animate-pulse rounded"
          />
        ))}
      </div>
    </div>
  );
}

function Empty({ title, subtitle, action, onAction }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <p className="text-app-muted text-sm">{title}</p>
      {subtitle && <p className="text-app-muted text-xs">{subtitle}</p>}
      {action && (
        <button
          type="button"
          onClick={onAction}
          className="text-app-text text-sm font-medium underline hover:no-underline"
        >
          {action}
        </button>
      )}
    </div>
  );
}

function Panel({ error }) {
  return (
    <div className="rounded-xl bg-red-50 px-4 py-6 text-center text-sm text-red-700">
      {error}
    </div>
  );
}
