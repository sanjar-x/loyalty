'use client';

import { useState } from 'react';
import { i18n } from '@/shared/lib/utils';

export function CategoryNode({ node, level = 0, onAddChild, onEdit }) {
  const [expanded, setExpanded] = useState(level === 0);
  const hasChildren = node.children?.length > 0;

  return (
    <div>
      <div
        className="group hover:bg-app-card flex items-center gap-1 rounded-lg px-2 py-1.5"
        style={{ paddingLeft: level * 24 + 8 }}
      >
        {hasChildren ? (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-app-muted flex h-5 w-5 shrink-0 items-center justify-center text-xs"
          >
            {expanded ? '▼' : '▶'}
          </button>
        ) : (
          <span className="text-app-muted flex h-5 w-5 shrink-0 items-center justify-center text-xs">
            •
          </span>
        )}

        <span className="text-app-text flex-1 truncate text-sm">
          {i18n(node.nameI18N)}
        </span>

        <span className="text-app-muted hidden text-xs group-hover:inline">
          {node.slug}
        </span>

        <div className="flex shrink-0 gap-0.5 opacity-0 group-hover:opacity-100">
          <button
            onClick={() => onAddChild(node.id)}
            className="text-app-muted hover:text-app-text flex h-6 w-6 items-center justify-center rounded text-sm hover:bg-[#e0dedb]"
            title="Добавить дочернюю"
          >
            +
          </button>
          <button
            onClick={() => onEdit(node)}
            className="text-app-muted hover:text-app-text flex h-6 w-6 items-center justify-center rounded text-sm hover:bg-[#e0dedb]"
            title="Редактировать"
          >
            ✎
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
