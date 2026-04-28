'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { listContexts } from '@/services/pricing/contexts';

const PricingPageContext = createContext(null);

export function PricingPageProvider({ children }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [contexts, setContexts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const contextId = searchParams.get('ctx') || null;
  const activeTab = searchParams.get('tab') || 'formula';

  const fetchContexts = useCallback(async () => {
    setError(null);
    try {
      const data = await listContexts();
      setContexts(data.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContexts();
  }, [fetchContexts]);

  useEffect(() => {
    if (!loading && contexts.length > 0 && !contextId) {
      const first = contexts[0];
      router.replace(`/admin/pricing?ctx=${first.contextId}&tab=formula`);
    }
  }, [loading, contexts, contextId, router]);

  const currentContext = useMemo(
    () => contexts.find((c) => c.contextId === contextId) ?? null,
    [contexts, contextId],
  );

  const setContextId = useCallback(
    (id) => {
      router.push(`/admin/pricing?ctx=${id}&tab=${activeTab}`);
    },
    [router, activeTab],
  );

  const setActiveTab = useCallback(
    (tab) => {
      if (contextId) {
        router.push(`/admin/pricing?ctx=${contextId}&tab=${tab}`);
      }
    },
    [router, contextId],
  );

  const value = useMemo(
    () => ({
      contexts,
      contextId,
      currentContext,
      activeTab,
      loading,
      error,
      setContextId,
      setActiveTab,
      refetchContexts: fetchContexts,
    }),
    [contexts, contextId, currentContext, activeTab, loading, error, setContextId, setActiveTab, fetchContexts],
  );

  return (
    <PricingPageContext.Provider value={value}>
      {children}
    </PricingPageContext.Provider>
  );
}

export function usePricingPage() {
  const ctx = useContext(PricingPageContext);
  if (!ctx) {
    throw new Error('usePricingPage must be used within PricingPageProvider');
  }
  return ctx;
}
