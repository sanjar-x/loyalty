import { CategoryNode } from './CategoryNode';

export function CategoryTree({ nodes, onAddChild, onEdit }) {
  if (!nodes?.length) {
    return null;
  }

  return (
    <div className="flex flex-col">
      {nodes.map((node) => (
        <CategoryNode
          key={node.id}
          node={node}
          level={0}
          onAddChild={onAddChild}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}
