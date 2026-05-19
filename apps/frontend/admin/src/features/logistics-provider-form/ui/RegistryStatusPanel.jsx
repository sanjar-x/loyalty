'use client';

import { PROVIDER_CODES, providerLabel } from '@/entities/logistics-provider';
import { cn } from '@/shared/lib/utils';
import { useProviderRegistryRefresh } from '../model/useProviderRegistryRefresh';

/**
 * «Состояние реестра» widget. The backend builds its provider registry at
 * process start; this panel is the operator's window into it — a manual
 * refresh plus the resulting `registeredProviderCodes`.
 *
 * It doubles as the health check: there is no "test connection" endpoint, so
 * a provider showing up in the registry after a refresh is the signal that
 * its credentials + config are valid. Absent = backend bootstrap rejected
 * the account (bad token / config).
 */
export function RegistryStatusPanel() {
  const { refreshRegistry, refreshing, lastResult } =
    useProviderRegistryRefresh();
  const registered = lastResult?.registeredProviderCodes ?? null;
  const extraCodes =
    registered?.filter((code) => !PROVIDER_CODES.includes(code)) ?? [];

  return (
    <div className="border-app-border bg-app-panel mb-5 rounded-2xl border p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-app-text-dark text-sm font-semibold">
            Состояние реестра
          </h3>
          <p className="text-app-muted mt-0.5 max-w-xl text-xs">
            Изменения провайдеров вступают в силу только после обновления
            in-memory реестра воркера. Провайдер в реестре — токен и конфиг
            валидны; отсутствует — backend его отклонил.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refreshRegistry()}
          disabled={refreshing}
          className="border-app-border text-app-text-dark hover:bg-app-card shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        >
          {refreshing ? 'Обновляем…' : 'Обновить реестр'}
        </button>
      </div>

      {registered ? (
        <>
          <ul className="mt-3 flex flex-wrap gap-2">
            {PROVIDER_CODES.map((code) => {
              const ok = registered.includes(code);
              return (
                <li
                  key={code}
                  className={cn(
                    'flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium',
                    ok
                      ? 'border-app-success/30 bg-app-success/10 text-app-success'
                      : 'border-app-border bg-app-card text-app-muted',
                  )}
                >
                  <span aria-hidden="true">{ok ? '✓' : '—'}</span>
                  {providerLabel(code)}
                  <span className="sr-only">
                    {ok ? 'в реестре' : 'не в реестре'}
                  </span>
                </li>
              );
            })}
            {extraCodes.map((code) => (
              <li
                key={code}
                className="border-app-border bg-app-card text-app-muted flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium"
              >
                <span aria-hidden="true">✓</span>
                {code}
              </li>
            ))}
          </ul>
          {lastResult?.note && (
            <p className="text-app-muted mt-2 text-xs italic">
              {lastResult.note}
            </p>
          )}
        </>
      ) : (
        <p className="text-app-muted mt-3 text-xs">
          Нажмите «Обновить реестр», чтобы проверить, какие провайдеры активны
          на backend.
        </p>
      )}
    </div>
  );
}
