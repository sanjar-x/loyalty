/**
 * Per-provider field descriptions — the single source of truth the provider
 * form renders from.
 *
 * Scope: only `yandex_delivery` has a real, provider-specific form. `cdek`
 * and `dobropost` are valid backend provider codes — they show up in the
 * list and the create picker — but their configuration forms ship as
 * separate tasks, so selecting them renders a "not implemented yet" stub.
 * `isProviderFormSupported` is the single gate for that.
 *
 * `credentials` / `config` are opaque dicts on the backend; these schemas
 * are what give them typed, provider-aware controls on the frontend.
 */

export const PROVIDER_CODES = ['cdek', 'yandex_delivery', 'dobropost'];

export const PROVIDER_LABELS = {
  cdek: 'CDEK',
  yandex_delivery: 'Yandex Delivery',
  dobropost: 'DobroPost',
};

/** 2-letter monogram for the card / picker avatar fallback. */
export const PROVIDER_MONOGRAM = {
  cdek: 'CD',
  yandex_delivery: 'YD',
  dobropost: 'DP',
};

/**
 * Providers with a built configuration form. CDEK / DobroPost are recognised
 * provider codes but their forms are separate tasks — the modal renders a
 * stub for anything not in this set.
 */
const FORM_SUPPORTED_PROVIDERS = new Set(['yandex_delivery']);

export function isProviderFormSupported(code) {
  return FORM_SUPPORTED_PROVIDERS.has(code);
}

/** One-line orientation shown under the provider picker. */
export const PROVIDER_HINTS = {
  yandex_delivery: 'OAuth-токен Яндекс Доставки из бизнес-кабинета.',
};

/**
 * `credentials` fields per provider. Write-only on the backend — reads return
 * only `credentialFingerprints`, and a PUT replaces the whole credentials
 * object, so the form submits every field of a provider at once. `secret`
 * renders a password input with a reveal toggle.
 */
const PROVIDER_CREDENTIALS = {
  yandex_delivery: [{ key: 'oauth_token', label: 'OAuth-токен', secret: true }],
};

/**
 * Provider-specific `config` fields — everything except `test_mode` and
 * `default_origin`, which the form renders with dedicated controls.
 *
 *   type      — text | number | select
 *   valueType — coercion target when it differs from the control type
 *               (e.g. a numeric `select` like the NDS code)
 *   section   — which form section the field belongs to: 'order' | 'http'
 *   unit      — suffix shown inside the control
 */
const PROVIDER_CONFIG_FIELDS = {
  yandex_delivery: [
    {
      key: 'payment_method',
      label: 'Способ оплаты по умолчанию',
      type: 'select',
      section: 'order',
      options: [
        { value: '', label: '— не задан —' },
        { value: 'already_paid', label: 'Уже оплачено' },
        { value: 'card_on_receipt', label: 'Картой при получении' },
        { value: 'postpay', label: 'Постоплата' },
      ],
    },
    {
      key: 'default_inn',
      label: 'ИНН по умолчанию',
      type: 'text',
      section: 'order',
      hint: 'Подставляется в billing_details товаров при создании отгрузки.',
    },
    {
      key: 'default_nds',
      label: 'НДС по умолчанию',
      type: 'select',
      valueType: 'number',
      section: 'order',
      options: [
        { value: '', label: '— не задан —' },
        { value: '0', label: '0%' },
        { value: '5', label: '5%' },
        { value: '7', label: '7%' },
        { value: '10', label: '10%' },
        { value: '22', label: '22%' },
        { value: '-1', label: 'Не облагается' },
      ],
    },
    {
      key: 'merchant_id',
      label: 'Merchant ID',
      type: 'text',
      section: 'order',
      hint: 'Только для мульти-мерчант аккаунтов Яндекс Доставки.',
    },
    {
      key: 'timeout_seconds',
      label: 'Тайм-аут запроса',
      type: 'number',
      unit: 'сек',
      section: 'http',
      placeholder: '30',
    },
    {
      key: 'max_retries',
      label: 'Повторов при сбое',
      type: 'number',
      section: 'http',
      placeholder: '3',
    },
  ],
};

/**
 * `default_origin` — sender-warehouse address, provider-specific. For Yandex
 * the rate resolver only reads `country_code` + `city` (both required);
 * `region` is cosmetic. CDEK's postal / street / house / lat / lng fields
 * belong to the CDEK form (a separate task) — they are inert for Yandex and
 * must not appear here.
 */
const PROVIDER_ORIGIN_FIELDS = {
  yandex_delivery: [
    {
      key: 'country_code',
      label: 'Код страны',
      placeholder: 'RU',
      required: true,
    },
    { key: 'city', label: 'Город', placeholder: 'Москва', required: true },
    {
      key: 'region',
      label: 'Регион',
      hint: 'Косметика — Yandex API это поле не использует.',
    },
  ],
};

/**
 * `default_origin.metadata` — provider-specific identifiers. For Yandex the
 * `platform_station_id` is the warehouse the API actually ships from, so it
 * is functionally required even though the backend stores it as opaque
 * metadata.
 */
const ORIGIN_METADATA_FIELDS = {
  yandex_delivery: [
    {
      key: 'platform_station_id',
      label: 'ID склада отгрузки',
      required: true,
      wide: true,
      hint: 'Platform Station ID — фактический склад-источник Яндекса. Без него API отклонит создание отгрузки.',
    },
  ],
};

export function providerLabel(code) {
  return PROVIDER_LABELS[code] ?? code;
}

export function credentialFields(code) {
  return PROVIDER_CREDENTIALS[code] ?? [];
}

export function configFields(code) {
  return PROVIDER_CONFIG_FIELDS[code] ?? [];
}

export function originFields(code) {
  return PROVIDER_ORIGIN_FIELDS[code] ?? [];
}

export function originMetadataFields(code) {
  return ORIGIN_METADATA_FIELDS[code] ?? [];
}
