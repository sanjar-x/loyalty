'use client';

import { useCallback, useState } from 'react';
import { refreshProviderRegistry } from '@/entities/logistics-provider';
import { useToast } from '@/shared/hooks/useToast';

/**
 * Registry-refresh orchestration shared by every provider-account surface
 * (form modal, delete modal, active toggle, and the standalone registry
 * status panel).
 *
 * Why this exists: the backend builds its in-memory provider registry at
 * process start. A DB write via create / update / delete / active is NOT
 * picked up by the running backend until `POST /refresh` runs — so we fire
 * it automatically after each mutation, and also expose it as the manual
 * button in the registry panel.
 *
 * The refresh only reaches the web instance that served the request; the
 * core-worker keeps its old registry until redeploy. We surface that
 * honestly (the backend's own `note`, plus a warning on failure) instead of
 * pretending the change is globally live. `lastResult` holds the most recent
 * `{ registeredProviderCodes, note }` so the panel can render it.
 */
export function useProviderRegistryRefresh() {
  const toast = useToast();
  const [refreshing, setRefreshing] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const refreshRegistry = useCallback(
    async (savedMessage) => {
      setRefreshing(true);
      try {
        const result = await refreshProviderRegistry();
        setLastResult(result ?? null);
        toast.success(
          savedMessage
            ? `${savedMessage}. Реестр провайдеров обновлён.`
            : 'Реестр провайдеров обновлён.',
        );
        if (result?.note) toast.info(result.note);
        return result ?? null;
      } catch {
        // The DB write already succeeded — a failed refresh only means the
        // running backend hasn't reloaded yet. Don't masquerade it as a
        // save failure; tell the operator what actually needs doing.
        toast.warning(
          savedMessage
            ? `${savedMessage}, но обновить реестр не удалось — ` +
                'изменения применятся после передеплоя backend.'
            : 'Не удалось обновить реестр провайдеров.',
        );
        return null;
      } finally {
        setRefreshing(false);
      }
    },
    [toast],
  );

  return { refreshRegistry, refreshing, lastResult };
}
