'use client';

import { useState } from 'react';
import { i18n } from '@/shared/lib/utils';

export function CategoryNode({ node, level = 0, onAddChild, onEdit }) {
  const [expanded, setExpanded] = useState(level === 0);
  const hasChildren = node.children?.length > 0;
  const nodeLabel = i18n(node.nameI18N);

  return (
    <div>
      <div
        className="group hover:bg-app-card focus-within:bg-app-card flex items-center gap-1 rounded-lg px-2 py-1.5"
        style={{ paddingLeft: level * 24 + 8 }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            aria-label={
              expanded
                ? `Свернуть категорию ${nodeLabel}`
                : `Развернуть категорию ${nodeLabel}`
            }
            className="text-app-muted flex h-5 w-5 shrink-0 items-center justify-center text-xs"
          >
            <span aria-hidden="true">{expanded ? '▼' : '▶'}</span>
          </button>
        ) : (
          <span
            aria-hidden="true"
            className="text-app-muted flex h-5 w-5 shrink-0 items-center justify-center text-xs"
          >
            •
          </span>
        )}

        <span className="text-app-text flex-1 truncate text-sm">
          {nodeLabel}
        </span>

        <span className="text-app-muted hidden text-xs group-focus-within:inline group-hover:inline">
          {node.slug}
        </span>

        {/*
          Audit 7.1 (P0): action buttons used to be `opacity-0 group-hover:opacity-100`
          which left them keyboard-focusable but visually invisible until a pointer
          hover. Reveal on focus-within as well so screen-reader / keyboard-only
          users see the actions when Tab lands inside the row.
        */}
        <div className="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          <button
            type="button"
            onClick={() => onAddChild(node.id)}
            aria-label={`Добавить подкатегорию в ${nodeLabel}`}
            title="Добавить дочернюю"
            className="text-app-muted hover:text-app-text focus-visible:text-app-text hover:bg-app-divider focus-visible:bg-app-divider flex h-6 w-6 items-center justify-center rounded text-sm"
          >
            <span aria-hidden="true">+</span>
          </button>
          <button
            type="button"
            onClick={() => onEdit(node)}
            aria-label={`Редактировать категорию ${nodeLabel}`}
            title="Редактировать"
            className="text-app-muted hover:text-app-text focus-visible:text-app-text hover:bg-app-divider focus-visible:bg-app-divider flex h-6 w-6 items-center justify-center rounded text-sm"
          >
            <span aria-hidden="true">✎</span>
          </button>
        </div>
      </div>

      {hasChildren && expanded && (
        <div>
          {node.children.map((child) => (
            <CategoryNode
              key={child.id}
              node={child}
              level={level + 1}
              onAddChild={onAddChild}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
    </div>
  );
}
