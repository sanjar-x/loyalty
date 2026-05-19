/**
 * Pure transforms between the backend `config` object and the structured
 * provider-form state.
 *
 * The form models every documented config key with a dedicated control, but
 * provider `config` is an opaque dict on the backend — so any key the schema
 * doesn't know about is preserved verbatim:
 *   - unknown top-level keys      → the "advanced JSON" textarea;
 *   - unknown default_origin keys → `originExtra`, merged back on submit;
 *   - unknown metadata keys       → `metadataExtra`, merged back on submit.
 *
 * Nothing the operator (or a prior curl-driven setup) put in `config` is ever
 * silently dropped — the senior counterpart to the MVP's raw-JSON tail.
 */

import {
  configFields,
  originFields,
  originMetadataFields,
} from './providerSchema';

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value
    : {};
}

function toInput(value, type) {
  if (value === undefined || value === null) return '';
  if (type === 'stringList') {
    return Array.isArray(value) ? value.join('\n') : String(value);
  }
  return String(value);
}

/** Backend `config` → structured form state for `providerCode`. */
export function splitConfigToForm(config, providerCode) {
  const cfg = asObject(config);
  const { test_mode: testMode, default_origin: defaultOrigin, ...rest } = cfg;

  // Provider-specific config fields.
  const fields = configFields(providerCode);
  const fieldKeys = new Set(fields.map((field) => field.key));
  const configValues = {};
  for (const field of fields) {
    configValues[field.key] = toInput(rest[field.key], field.type);
  }

  // Anything left over at the top level → advanced JSON escape hatch.
  const advanced = {};
  for (const [key, value] of Object.entries(rest)) {
    if (!fieldKeys.has(key)) advanced[key] = value;
  }

  // default_origin — known (provider-specific) fields structured, the rest
  // preserved.
  const origin = asObject(defaultOrigin);
  const { metadata, ...originRest } = origin;
  const originDefs = originFields(providerCode);
  const originKeys = new Set(originDefs.map((field) => field.key));
  const originValues = {};
  for (const field of originDefs) {
    originValues[field.key] = toInput(originRest[field.key], field.type);
  }
  const originExtra = {};
  for (const [key, value] of Object.entries(originRest)) {
    if (!originKeys.has(key)) originExtra[key] = value;
  }

  // default_origin.metadata — provider-specific, same known/extra split.
  const metaFields = originMetadataFields(providerCode);
  const metaKeys = new Set(metaFields.map((field) => field.key));
  const metaObj = asObject(metadata);
  const metadataValues = {};
  for (const field of metaFields) {
    metadataValues[field.key] = toInput(metaObj[field.key]);
  }
  const metadataExtra = {};
  for (const [key, value] of Object.entries(metaObj)) {
    if (!metaKeys.has(key)) metadataExtra[key] = value;
  }

  return {
    testMode: Boolean(testMode),
    configValues,
    originValues,
    metadataValues,
    originExtra,
    metadataExtra,
    advancedText: Object.keys(advanced).length
      ? JSON.stringify(advanced, null, 2)
      : '',
  };
}

function coerce(raw, type) {
  const text = String(raw ?? '').trim();
  if (!text) return undefined;
  if (type === 'number') {
    const num = Number(text);
    return Number.isFinite(num) ? num : undefined;
  }
  if (type === 'stringList') {
    const list = text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    return list.length ? list : undefined;
  }
  return text;
}

/**
 * Structured form state → backend `config`. Sent whole with
 * `replaceConfig: true`, so this is the complete object — the form is the
 * source of truth. `form.advancedText` must be valid JSON; the modal gates
 * submit on it.
 */
export function buildConfigFromForm(form, providerCode) {
  const config = {};

  // Advanced JSON has the lowest priority — structured fields win.
  if (form.advancedText && form.advancedText.trim()) {
    const parsed = JSON.parse(form.advancedText);
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      Object.assign(config, parsed);
    }
  }

  for (const field of configFields(providerCode)) {
    // A numeric `select` (e.g. NDS code) coerces via `valueType`, not the
    // control type.
    const value = coerce(
      form.configValues[field.key],
      field.valueType ?? field.type,
    );
    if (value !== undefined) config[field.key] = value;
  }

  config.test_mode = Boolean(form.testMode);

  const origin = { ...form.originExtra };
  for (const field of originFields(providerCode)) {
    const value = coerce(form.originValues[field.key], field.type);
    if (value !== undefined) origin[field.key] = value;
  }

  const metadata = { ...form.metadataExtra };
  for (const field of originMetadataFields(providerCode)) {
    const value = coerce(form.metadataValues[field.key], field.valueType);
    if (value !== undefined) metadata[field.key] = value;
  }
  if (Object.keys(metadata).length) origin.metadata = metadata;
  if (Object.keys(origin).length) config.default_origin = origin;

  return config;
}

/** Short "City, CC" summary of a stored `config.default_origin` for the card. */
export function originSummary(config) {
  const origin = asObject(asObject(config).default_origin);
  return [origin.city, origin.country_code].filter(Boolean).join(', ');
}
