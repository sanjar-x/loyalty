'use client';

import { useState } from 'react';
import {
  ContextSwitcher,
  ContextHeader,
  PricingTabs,
  usePricingPage,
  EmptyState,
  ErrorBanner,
  LoadingSkeleton,
  FormulaTab,
  VariablesTab,
  CategoriesTab,
  ContextSettingsTab,
  CreateContextModal,
} from '@/features/pricing';

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
  const { contexts, loading, error, contextId, refetchContexts } =
    usePricingPage();
  const [showCreateModal, setShowCreateModal] = useState(false);

  if (loading) {
    return (
      <section className="animate-fadeIn">
        <h1 className="text-app-text-dark mb-5 text-[40px] leading-[44px] font-bold tracking-tight">
          Формулы цен
        </h1>
        <div className="border-app-border-soft rounded-2xl border bg-white p-5">
          <LoadingSkeleton rows={6} columns={4} />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="animate-fadeIn">
        <h1 className="text-app-text-dark mb-5 text-[40px] leading-[44px] font-bold tracking-tight">
          Формулы цен
        </h1>
        <ErrorBanner error={error} />
      </section>
    );
  }

  if (contexts.length === 0) {
    return (
      <section className="animate-fadeIn">
        <h1 className="text-app-text-dark mb-5 text-[40px] leading-[44px] font-bold tracking-tight">
          Формулы цен
        </h1>
        <div className="border-app-border-soft rounded-2xl border bg-white p-5">
          <EmptyState
            title="Нет контекстов ценообразования"
            description="Создайте первый ценовой контекст, чтобы начать настройку формул."
            action={{
              label: '+ Создать контекст',
              onClick: () => setShowCreateModal(true),
            }}
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
        <h1 className="text-app-text-dark text-[40px] leading-[44px] font-bold tracking-tight">
          Формулы цен
        </h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Контекст
        </button>
      </div>

      <div className="border-app-border-soft rounded-2xl border bg-white p-5">
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
