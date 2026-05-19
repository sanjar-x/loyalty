import {
  ProviderLogo,
  ProviderName,
  providerLabel,
} from '@/entities/logistics-provider';

/**
 * Placeholder shown when an operator picks a provider whose configuration
 * form is not built yet (CDEK / DobroPost — separate tasks). The provider is
 * a valid backend code; only its provider-specific form is missing, so the
 * copy points at the API as the current path rather than implying the
 * provider is unsupported.
 */
export function ProviderFormStub({ code }) {
  return (
    <div className="border-app-border bg-app-card/40 flex flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-10 text-center">
      <ProviderLogo code={code} className="h-12 w-12 rounded-xl" />
      <div>
        <ProviderName
          code={code}
          className="text-app-text-dark text-sm font-semibold"
          logoClassName="mx-auto h-5"
        />
        <p className="text-app-muted mx-auto mt-1.5 max-w-sm text-sm">
          Форма настройки {providerLabel(code)} ещё не реализована — это
          отдельная задача. Пока аккаунт этого провайдера заводится прямыми
          вызовами API.
        </p>
      </div>
    </div>
  );
}
