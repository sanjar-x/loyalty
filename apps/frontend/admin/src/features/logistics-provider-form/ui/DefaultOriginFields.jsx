'use client';

import {
  originFields,
  originMetadataFields,
} from '@/entities/logistics-provider';
import { FormField } from './FormFields';

/**
 * Structured `default_origin` sub-form — the sender-warehouse address the
 * backend rate resolver needs. Origin fields and provider metadata
 * (`default_origin.metadata`, e.g. Yandex `platform_station_id`) render in
 * one continuous grid; the metadata vs top-level split is a serialisation
 * detail the operator never sees.
 *
 * Field definitions are provider-specific — for Yandex this is just country
 * code / city / region + the platform station id. CDEK's postal/street/house
 * fields live in the CDEK form (a separate task).
 */
export function DefaultOriginFields({
  providerCode,
  values,
  metadata,
  errors,
  metadataErrors,
  onChangeValue,
  onChangeMetadata,
  disabled = false,
}) {
  const fields = originFields(providerCode);
  const metaFields = originMetadataFields(providerCode);

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fields.map((field) => (
        <div
          key={field.key}
          className={field.wide ? 'sm:col-span-2' : undefined}
        >
          <FormField
            label={field.label}
            type={field.type === 'number' ? 'number' : 'text'}
            required={field.required}
            placeholder={field.placeholder}
            hint={field.hint}
            value={values[field.key] ?? ''}
            error={errors?.[field.key]}
            disabled={disabled}
            onChange={(next) => onChangeValue(field.key, next)}
          />
        </div>
      ))}
      {metaFields.map((field) => (
        <div
          key={field.key}
          className={field.wide ? 'sm:col-span-2' : undefined}
        >
          <FormField
            label={field.label}
            required={field.required}
            placeholder={field.placeholder}
            hint={field.hint}
            value={metadata[field.key] ?? ''}
            error={metadataErrors?.[field.key]}
            disabled={disabled}
            onChange={(next) => onChangeMetadata(field.key, next)}
          />
        </div>
      ))}
    </div>
  );
}
