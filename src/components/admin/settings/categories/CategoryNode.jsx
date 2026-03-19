'use client';

import { useState } from 'react';

export function CategoryNode({ node, level = 0, onAddChild, onEdit }) {
  const [expanded, setExpanded] = useState(level === 0);
  const hasChildren = node.children?.length > 0;

  return (
    <div>
      <div
        className="group flex items-center gap-1 rounded-lg px-2 py-1.5 hover:bg-[#f4f3f1]"
        style={{ paddingLeft: level * 24 + 8 }}
      >
        {hasChildren ? (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex h-5 w-5 shrink-0 items-center justify-center text-xs text-[#878b93]"
          >
            {expanded ? '▼' : '▶'}
          </button>
        ) : (
          <span className="flex h-5 w-5 shrink-0 items-center justify-center text-xs text-[#878b93]">
            •
          </span>
        )}

        <span className="flex-1 truncate text-sm text-[#22252b]">
          {node.name}
        </span>

        <span className="hidden text-xs text-[#878b93] group-hover:inline">
          {node.slug}
        </span>

        <div className="flex shrink-0 gap-0.5 opacity-0 group-hover:opacity-100">
          <button
            onClick={() => onAddChild(node.id)}
            className="flex h-6 w-6 items-center justify-center rounded text-sm text-[#878b93] hover:bg-[#e0dedb] hover:text-[#22252b]"
            title="Добавить дочернюю"
          >
            +
          </button>
          <button
            onClick={() => onEdit(node)}
            className="flex h-6 w-6 items-center justify-center rounded text-sm text-[#878b93] hover:bg-[#e0dedb] hover:text-[#22252b]"
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
