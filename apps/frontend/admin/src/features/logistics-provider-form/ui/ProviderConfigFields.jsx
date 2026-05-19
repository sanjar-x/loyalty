'use client';

import { useId } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import { cn } from '@/shared/lib/utils';
import { FormField, INPUT_CLASS } from './FormFields';

function controlType(field) {
  if (field.type === 'select') return 'select';
  if (field.type === 'stringList') return 'stringList';
  if (field.type === 'number') return 'number';
  return field.secret ? 'password' : 'text';
}

/**
 * A grid of provider `config` fields rendered from the entity schema. The
 * modal decides the grouping (e.g. "Параметры заказа" vs "HTTP-клиент") and
 * passes the matching `fields` slice — this component only lays the controls
 * out.
 */
export function ConfigFieldGrid({
  fields,
  values,
  errors,
  onChange,
  disabled = false,
}) {
  if (!fields?.length) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fields.map((field) => (
        <div key={field.key} className={cn(field.wide && 'sm:col-span-2')}>
          <FormField
            label={field.label}
            type={controlType(field)}
            options={field.options}
            unit={field.unit}
            placeholder={field.placeholder}
            hint={field.hint}
            error={errors?.[field.key]}
            mono={field.type === 'stringList'}
            value={values[field.key] ?? ''}
            disabled={disabled}
            onChange={(next) => onChange(field.key, next)}
          />
        </div>
      ))}
    </div>
  );
}

/**
 * Collapsible "advanced JSON" escape hatch. Carries only the config keys the
 * structured form doesn't model — `splitConfigToForm` routes everything else
 * into typed controls — so no curl-era config value is ever silently lost.
 */
export function AdvancedConfigField({
  value,
  error,
  open,
  onToggle,
  onChange,
  disabled = false,
}) {
  const id = useId();

  return (
    <div className="border-app-border rounded-lg border">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-controls={id}
        className="text-app-text-dark hover:bg-app-card flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors"
      >
        <span>Расширенная конфигурация (JSON)</span>
        <ChevronIcon
          className={cn(
            'text-app-muted h-4 w-4 transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>
      {open && (
        <div id={id} className="border-app-border border-t p-3">
          <textarea
            value={value}
            onChange={(event) => onChange(event.target.value)}
            disabled={disabled}
            rows={6}
            spellCheck={false}
            placeholder="{}"
            className={cn(INPUT_CLASS, 'font-mono')}
            aria-label="Расширенная конфигурация в формате JSON"
            aria-invalid={error ? true : undefined}
          />
          <p className="text-app-muted mt-1 text-xs">
            Только ключи, которых нет в форме выше — сохраняются как есть.
          </p>
          {error && (
            <p role="alert" className="text-app-danger mt-1 text-xs">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
