'use client';

import CloseIcon from '@/assets/icons/close.svg';
import PencilIcon from '@/assets/icons/pencil.svg';
import { credentialFields } from '@/entities/logistics-provider';
import { cn, pluralizeRu } from '@/shared/lib/utils';
import { FormField } from './FormFields';

function LockIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      aria-hidden="true"
    >
      <rect x="3" y="7" width="10" height="6.5" rx="1.6" />
      <path d="M5.5 7V5.2a2.5 2.5 0 0 1 5 0V7" strokeLinecap="round" />
    </svg>
  );
}

/**
 * One credential row. Edits inline — the masked display swaps to an input
 * in place, in the same card, and the pencil affordance becomes a cancel
 * (✕). Editing is section-level on purpose: a PUT replaces the whole
 * credentials object, so revealing one input reveals them all.
 *
 * The masked view is built from the backend fingerprint — raw values never
 * leave the server. The label comes from the provider schema, so operators
 * see "OAuth-токен", not `oauth_token`.
 */
function CredentialRow({
  field,
  fingerprint,
  value,
  onChange,
  editing,
  onToggle,
  disabled,
  error,
}) {
  const isSet = Boolean(fingerprint);

  return (
    <li
      className={cn(
        'border-app-border flex gap-3 rounded-xl border px-3.5 py-3',
        editing ? 'items-start' : 'items-center',
      )}
    >
      <span
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
          isSet
            ? 'bg-app-success/10 text-app-success'
            : 'bg-app-card text-app-muted',
        )}
      >
        <LockIcon className="h-4 w-4" />
      </span>

      <div className="min-w-0 flex-1">
        {editing ? (
          <FormField
            label={field.label}
            type={field.secret ? 'password' : 'text'}
            required
            mono
            value={value}
            error={error}
            disabled={disabled}
            onChange={onChange}
          />
        ) : (
          <>
            <p className="text-app-text-dark text-sm font-medium">
              {field.label}
            </p>
            {isSet ? (
              <p className="text-app-muted mt-0.5 text-xs">
                <span
                  aria-hidden="true"
                  className="text-app-text-secondary tracking-[0.2em]"
                >
                  ••••••••
                </span>{' '}
                ·{' '}
                <span
                  className="text-app-text-secondary font-mono"
                  title="Отпечаток ключа (SHA-256)"
                >
                  {fingerprint.fingerprint}
                </span>{' '}
                · {fingerprint.length}{' '}
                {pluralizeRu(
                  fingerprint.length,
                  'символ',
                  'символа',
                  'символов',
                )}
              </p>
            ) : (
              <p className="text-app-muted mt-0.5 text-xs">не задан</p>
            )}
          </>
        )}
      </div>

      {onToggle && (
        <button
          type="button"
          onClick={onToggle}
          disabled={disabled}
          title={editing ? 'Отменить замену' : 'Заменить учётные данные'}
          aria-label={
            editing
              ? `Отменить замену: ${field.label}`
              : `Заменить: ${field.label}`
          }
          className="border-app-border text-app-muted hover:text-app-text-dark hover:bg-app-card flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        >
          {editing ? (
            <CloseIcon className="h-3.5 w-3.5" />
          ) : (
            <PencilIcon className="h-4 w-4" />
          )}
        </button>
      )}
    </li>
  );
}

/**
 * Credentials block — inline "secrets" editing. Each provider credential is
 * a row that flips between a read-only masked view and an inline input. In
 * create mode every row starts as an input.
 *
 * `errors` (keyed by credential key) carries required-field messages while a
 * row is in input mode — surfaced by the modal after a submit attempt.
 */
export function CredentialsSection({
  providerCode,
  fingerprints,
  values,
  onChange,
  isEdit,
  changing,
  onChangingChange,
  disabled = false,
  errors,
}) {
  const fields = credentialFields(providerCode);
  // Input mode for every row — always in create, on demand in edit.
  const editing = !isEdit || changing;

  return (
    <ul className="space-y-2">
      {fields.map((field) => (
        <CredentialRow
          key={field.key}
          field={field}
          fingerprint={fingerprints?.[field.key]}
          value={values[field.key] ?? ''}
          onChange={(next) => onChange(field.key, next)}
          editing={editing}
          onToggle={isEdit ? () => onChangingChange(!changing) : undefined}
          disabled={disabled}
          error={editing ? errors?.[field.key] : undefined}
        />
      ))}
    </ul>
  );
}
