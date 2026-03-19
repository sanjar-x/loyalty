'use client';

import { useState, useEffect, useCallback } from 'react';
import { CategoryTree } from '@/components/admin/settings/categories/CategoryTree';
import { CategoryModal } from '@/components/admin/settings/categories/CategoryModal';
import { CategorySkeleton } from '@/components/admin/settings/categories/CategorySkeleton';

export default function CategoriesPage() {
  const [tree, setTree] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);

  const fetchTree = useCallback(async () => {
    try {
      const res = await fetch('/api/categories/tree');
      if (res.ok) {
        const data = await res.json();
        setTree(data);
      }
    } catch {
      // silent — tree stays empty
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

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
        name: category.name,
        slug: category.slug,
        sortOrder: category.sortOrder,
      },
    });
  }

  function handleModalSuccess() {
    setModal(null);
    setLoading(true);
    fetchTree();
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-[#22252b]">Категории</h2>
        <button
          onClick={handleAddRoot}
          className="rounded-lg bg-[#22252b] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Добавить
        </button>
      </div>

      {loading ? (
        <CategorySkeleton />
      ) : tree.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-[#878b93]">Категории не добавлены</p>
          <button
            onClick={handleAddRoot}
            className="text-sm font-medium text-[#22252b] underline hover:no-underline"
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
