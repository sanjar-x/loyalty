'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  CategoryTree,
  CategoryModal,
  CategorySkeleton,
  categoryKeys,
  useCategoryTree,
} from '@/entities/category';
import { i18n } from '@/shared/lib/utils';

export default function CategoriesPage() {
  const queryClient = useQueryClient();
  const { data: tree = [], isPending: loading } = useCategoryTree();
  const [modal, setModal] = useState(null);

  function handleAddRoot() {
    setModal({ mode: 'create', parentId: null });
  }

  function handleAddChild(parentId) {
    setModal({ mode: 'create', parentId });
  }

  function handleEdit(category) {
    setModal({
      mode: 'edit',
      category: {
        id: category.id,
        name: i18n(category.nameI18N),
        slug: category.slug,
        sortOrder: category.sortOrder,
      },
    });
  }

  function handleModalSuccess() {
    setModal(null);
    queryClient.invalidateQueries({ queryKey: categoryKeys.all });
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-app-text text-xl font-semibold">Категории</h2>
        <button
          onClick={handleAddRoot}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Добавить
        </button>
      </div>

      {loading ? (
        <CategorySkeleton />
      ) : tree.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-app-muted text-sm">Категории не добавлены</p>
          <button
            onClick={handleAddRoot}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Добавить первую
          </button>
        </div>
      ) : (
        <CategoryTree
          nodes={tree}
          onAddChild={handleAddChild}
          onEdit={handleEdit}
        />
      )}

      {modal && (
        <CategoryModal
          mode={modal.mode}
          parentId={modal.parentId}
          category={modal.category}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
    </div>
  );
}
