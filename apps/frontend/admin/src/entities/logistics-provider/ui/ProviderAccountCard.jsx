'use client';

import { useMemo } from 'react';
import PencilIcon from '@/assets/icons/pencil.svg';
import TrashIcon from '@/assets/icons/trash.svg';
import { Badge } from '@/shared/ui/Badge';
import { cn, formatDateTime } from '@/shared/lib/utils';
import { originSummary } from '../lib/configForm';
import { credentialFields } from '../lib/providerSchema';
import { ProviderLogo } from './ProviderLogo';
import { ProviderName } from './ProviderName';

/**
 * Read-only provider-account card. Every action is wired by the page layer
 * through props — the entity stays free of mutations, same pattern as
 * BrandRow.
 *
 * Surfaces the operationally important state at a glance: test-mode,
 * sender-warehouse city, and the credential fingerprints (the only window
 * into the stored credentials — raw values never leave the backend).
 */
export function ProviderAccountCard({
  account,
  onEdit,
  onDelete,
  onToggleActive,
  toggling = false,
}) {
  const fingerprints = Object.entries(account.credentialFingerprints ?? {});
  const origin = originSummary(account.config);
  const testMode = Boolean(account.config?.test_mode);

  // `oauth_token` → "OAuth-токен" so the card speaks the operator's language;
  // unknown keys (or stub providers) fall back to the raw key.
  const credLabels = useMemo(() => {
    const map = {};
    for (const field of credentialFields(account.providerCode)) {
      map[field.key] = field.label;
    }
    return map;
  }, [account.providerCode]);

  return (
    <article
      className={cn(
        'border-app-border bg-app-panel hover:shadow-soft rounded-2xl border p-5 transition-shadow',
        !account.isActive && 'opacity-[0.82]',
      )}
    >
      <div className="flex items-start gap-4">
        <ProviderLogo
          code={account.providerCode}
          className="h-11 w-11 rounded-xl"
        />

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="text-app-text-dark text-base font-semibold">
              {account.name}
            </h3>
            {testMode && <Badge variant="china">Тестовый режим</Badge>}
          </div>
          <ProviderName
            code={account.providerCode}
            className="text-app-muted mt-0.5 block text-sm"
            logoClassName="mt-1 h-5"
          />

          <dl className="mt-3 grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
            <div className="flex flex-col">
              <dt className="text-app-muted text-xs">Склад-отправитель</dt>
              <dd
                className={cn(
                  'text-sm',
                  origin ? 'text-app-text-dark' : 'text-app-danger',
                )}
              >
                {origin || 'не задан — расчёт доставки не сработает'}
              </dd>
            </div>
            <div className="flex flex-col">
              <dt className="text-app-muted text-xs">Обновлён</dt>
              <dd className="text-app-text-dark text-sm">
                {formatDateTime(account.updatedAt)}
              </dd>
            </div>
          </dl>

          {fingerprints.length > 0 && (
            <div className="mt-3">
              <p className="text-app-muted text-xs">Учётные данные</p>
              <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                {fingerprints.map(([key, fp]) => (
                  <li key={key} className="text-app-text-secondary text-xs">
                    {credLabels[key] ?? key} ·{' '}
                    <span className="text-app-text-dark font-mono">
                      {fp?.fingerprint ?? '—'}
                    </span>{' '}
                    · {fp?.length ?? 0} симв.
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col items-end gap-3">
          <StatusToggle
            active={account.isActive}
            disabled={toggling}
            onToggle={() => onToggleActive?.(account)}
          />
          <div className="flex gap-1">
            <IconButton
              icon={PencilIcon}
              label="Редактировать"
              onClick={() => onEdit?.(account)}
            />
            <IconButton
              icon={TrashIcon}
              label="Удалить"
              danger
              onClick={() => onDelete?.(account)}
            />
          </div>
        </div>
      </div>
    </article>
  );
}

/**
 * Accessible on/off switch — the primary affordance for account status.
 * The off-state track uses `bg-app-muted` (not `bg-app-border`) so the
 * control stays visible against the white card.
 */
function StatusToggle({ active, disabled, onToggle }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          'text-xs font-medium',
          active ? 'text-app-success' : 'text-app-muted',
        )}
      >
        {active ? 'Активен' : 'Отключён'}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={active}
        aria-label={active ? 'Отключить провайдера' : 'Активировать провайдера'}
        disabled={disabled}
        onClick={onToggle}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full transition-colors',
          'focus-visible:ring-app-text-dark/25 focus-visible:ring-2 focus-visible:outline-none',
          'disabled:cursor-not-allowed disabled:opacity-50',
          active ? 'bg-app-success' : 'bg-app-muted',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
            active ? 'translate-x-5' : 'translate-x-0',
          )}
        />
      </button>
    </div>
  );
}

function IconButton({ icon: Icon, label, onClick, danger = false }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={cn(
        'flex h-8 w-8 items-center justify-center rounded-lg border transition-colors',
        danger
          ? 'border-red-200 text-red-600 hover:bg-red-50'
          : 'border-app-border text-app-muted hover:text-app-text-dark hover:bg-app-card',
      )}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
