'use client';

import { useState } from 'react';
import { ContextSwitcher } from '@/components/admin/pricing/ContextSwitcher';
import { ContextHeader } from '@/components/admin/pricing/ContextHeader';
import { PricingTabs } from '@/components/admin/pricing/PricingTabs';
import { usePricingPage } from '@/components/admin/pricing/PricingPageProvider';
import { EmptyState } from '@/components/admin/pricing/shared/EmptyState';
import { ErrorBanner } from '@/components/admin/pricing/shared/ErrorBanner';
import { LoadingSkeleton } from '@/components/admin/pricing/shared/LoadingSkeleton';
import { FormulaTab } from '@/components/admin/pricing/formula/FormulaTab';
import { VariablesTab } from '@/components/admin/pricing/variables/VariablesTab';
import { CategoriesTab } from '@/components/admin/pricing/categories/CategoriesTab';
import { ContextSettingsTab } from '@/components/admin/pricing/context/ContextSettingsTab';
import { CreateContextModal } from '@/components/admin/pricing/context/CreateContextModal';

function TabContent() {
  const { activeTab, contextId } = usePricingPage();

  if (!contextId) return null;

  switch (activeTab) {
    case 'formula':
      return <FormulaTab />;
    case 'variables':
      return <VariablesTab />;
    case 'categories':
      return <CategoriesTab />;
    case 'settings':
      return <ContextSettingsTab />;
    default:
      return <FormulaTab />;
  }
}

export default function PricingPage() {
  const { contexts, loading, error, contextId, refetchContexts } = usePricingPage();
  const [showCreateModal, setShowCreateModal] = useState(false);

  if (loading) {
    return (
      <section className="animate-fadeIn">
        <h1 className="mb-5 text-[40px] font-bold leading-[44px] tracking-tight text-app-text-dark">
          Формулы цен
        </h1>
        <div className="rounded-2xl border border-[#f0f0f0] bg-white p-5">
          <LoadingSkeleton rows={6} columns={4} />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="animate-fadeIn">
        <h1 className="mb-5 text-[40px] font-bold leading-[44px] tracking-tight text-app-text-dark">
          Формулы цен
        </h1>
        <ErrorBanner error={error} />
      </section>
    );
  }

  if (contexts.length === 0) {
    return (
      <section className="animate-fadeIn">
        <h1 className="mb-5 text-[40px] font-bold leading-[44px] tracking-tight text-app-text-dark">
          Формулы цен
        </h1>
        <div className="rounded-2xl border border-[#f0f0f0] bg-white p-5">
          <EmptyState
            title="Нет контекстов ценообразования"
            description="Создайте первый ценовой контекст, чтобы начать настройку формул."
            action={{ label: '+ Создать контекст', onClick: () => setShowCreateModal(true) }}
          />
        </div>
        {showCreateModal && (
          <CreateContextModal
            onClose={() => setShowCreateModal(false)}
            onSuccess={() => {
              setShowCreateModal(false);
              refetchContexts();
            }}
          />
        )}
      </section>
    );
  }

  return (
    <section className="animate-fadeIn">
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-[40px] font-bold leading-[44px] tracking-tight text-app-text-dark">
          Формулы цен
        </h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Контекст
        </button>
      </div>

      <div className="rounded-2xl border border-[#f0f0f0] bg-white p-5">
        <div className="flex flex-col gap-4">
          <ContextSwitcher />
          {contextId && (
            <>
              <ContextHeader />
              <PricingTabs>
                <TabContent />
              </PricingTabs>
            </>
          )}
        </div>
      </div>

      {showCreateModal && (
        <CreateContextModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            refetchContexts();
          }}
        />
      )}
    </section>
  );
}
