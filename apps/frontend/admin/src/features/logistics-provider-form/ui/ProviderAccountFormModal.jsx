'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import {
  PROVIDER_CODES,
  PROVIDER_HINTS,
  ProviderLogo,
  ProviderName,
  buildConfigFromForm,
  configFields,
  credentialFields,
  isProviderFormSupported,
  originFields,
  originMetadataFields,
  splitConfigToForm,
  useCreateProviderAccount,
  useProviderAccount,
  useUpdateProviderAccount,
} from '@/entities/logistics-provider';
import { Modal } from '@/shared/ui/Modal';
import { Skeleton } from '@/shared/ui/Skeleton';
import { cn } from '@/shared/lib/utils';
import { useProviderRegistryRefresh } from '../model/useProviderRegistryRefresh';
import { CheckboxRow, FormField } from './FormFields';
import { CredentialsSection } from './CredentialsSection';
import { DefaultOriginFields } from './DefaultOriginFields';
import { AdvancedConfigField, ConfigFieldGrid } from './ProviderConfigFields';
import { ProviderFormStub } from './ProviderFormStub';

const EMPTY_FORM = splitConfigToForm({}, '');
const REQUIRED = 'Обязательное поле';

function buildCredentials(fields, values) {
  return Object.fromEntries(
    fields.map((field) => [field.key, String(values[field.key] ?? '').trim()]),
  );
}

function isFilled(value) {
  return String(value ?? '').trim().length > 0;
}

/** Section heading + body — gives the long form a clear scannable rhythm. */
function Section({ title, description, children }) {
  return (
    <section className="space-y-3">
      <div>
        <h3 className="text-app-text-dark text-sm font-semibold">{title}</h3>
        {description && (
          <p className="text-app-muted mt-0.5 text-xs">{description}</p>
        )}
      </div>
      {children}
    </section>
  );
}

/** Collapsible section — used for the optional "HTTP-клиент" block. */
function CollapsibleSection({ title, description, children }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <section className="border-app-border rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls={id}
        className="hover:bg-app-card flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors"
      >
        <span>
          <span className="text-app-text-dark block text-sm font-semibold">
            {title}
          </span>
          {description && (
            <span className="text-app-muted block text-xs">{description}</span>
          )}
        </span>
        <ChevronIcon
          className={cn(
            'text-app-muted h-4 w-4 shrink-0 transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>
      {open && (
        <div id={id} className="border-app-border border-t p-3">
          {children}
        </div>
      )}
    </section>
  );
}

/** Segmented provider picker — visual, shows the available providers upfront. */
function ProviderPicker({ value, onChange, disabled }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {PROVIDER_CODES.map((code) => {
        const selected = value === code;
        return (
          <button
            key={code}
            type="button"
            disabled={disabled}
            aria-pressed={selected}
            onClick={() => onChange(code)}
            className={cn(
              'flex flex-col items-center gap-2 rounded-xl border p-3 text-center transition-colors',
              selected
                ? 'border-app-text-dark bg-app-card'
                : 'border-app-border hover:bg-app-card',
              disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            <ProviderLogo code={code} className="h-9 w-9 rounded-lg" />
            <ProviderName
              code={code}
              className="text-app-text-dark text-xs font-medium"
              logoClassName="h-4"
            />
          </button>
        );
      })}
    </div>
  );
}

function EditSkeleton() {
  return (
    <div
      className="mt-4 space-y-4"
      role="status"
      aria-label="Загружаем провайдера"
    >
      <Skeleton.Bar w="35%" />
      <Skeleton.Block h={56} />
      <Skeleton.Block h={120} />
      <Skeleton.Block h={180} />
    </div>
  );
}

/**
 * Unified create / edit provider-account modal. Only `yandex_delivery` has a
 * full provider-specific form (this task) — CDEK / DobroPost render a stub.
 * The Yandex form is structured and dynamic by schema: credential / config /
 * origin fields all come from the entity provider-schema, and an "advanced
 * JSON" hatch preserves any non-modelled config keys.
 *
 * Two backend quirks shape the submit logic:
 *   • credentials replace the whole object on PUT — so in edit mode they are
 *     only sent behind an explicit "change credentials" toggle;
 *   • config merges shallowly — so we always send the full object built by
 *     `buildConfigFromForm` with `replaceConfig: true` (the form is the
 *     source of truth).
 */
export function ProviderAccountFormModal({
  open,
  onClose,
  mode = 'create',
  accountId,
}) {
  const isEdit = mode === 'edit';
  const { data: existing, isPending: existingPending } = useProviderAccount(
    isEdit && open ? accountId : null,
  );

  const createMutation = useCreateProviderAccount();
  const updateMutation = useUpdateProviderAccount(accountId);
  const mutation = isEdit ? updateMutation : createMutation;
  const { refreshRegistry } = useProviderRegistryRefresh();

  const [providerCode, setProviderCode] = useState('');
  const [name, setName] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [credentials, setCredentials] = useState({});
  const [changeCredentials, setChangeCredentials] = useState(true);

  const [testMode, setTestMode] = useState(false);
  const [configValues, setConfigValues] = useState({});
  const [originValues, setOriginValues] = useState(EMPTY_FORM.originValues);
  const [metadataValues, setMetadataValues] = useState({});
  const [advancedText, setAdvancedText] = useState('');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [submitAttempted, setSubmitAttempted] = useState(false);

  // Unknown config keys are preserved verbatim across an edit round-trip.
  const originExtraRef = useRef({});
  const metadataExtraRef = useRef({});

  // Reset + seed on (re)open. Edit waits for the GET /{id} snapshot so the
  // form mirrors the live config the operator is about to replace.
  useEffect(() => {
    if (!open) return;
    mutation.reset();
    setSubmitAttempted(false);
    if (isEdit) {
      if (!existing) return;
      const code = existing.providerCode ?? '';
      const form = splitConfigToForm(existing.config, code);
      setProviderCode(code);
      setName(existing.name ?? '');
      setIsActive(existing.isActive ?? true);
      setCredentials({});
      setChangeCredentials(false);
      setTestMode(form.testMode);
      setConfigValues(form.configValues);
      setOriginValues(form.originValues);
      setMetadataValues(form.metadataValues);
      setAdvancedText(form.advancedText);
      setAdvancedOpen(Boolean(form.advancedText));
      originExtraRef.current = form.originExtra;
      metadataExtraRef.current = form.metadataExtra;
    } else {
      setProviderCode('');
      setName('');
      setIsActive(true);
      setCredentials({});
      setChangeCredentials(true);
      setTestMode(false);
      setConfigValues({});
      setOriginValues(EMPTY_FORM.originValues);
      setMetadataValues({});
      setAdvancedText('');
      setAdvancedOpen(false);
      originExtraRef.current = {};
      metadataExtraRef.current = {};
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isEdit, existing?.id]);

  const supported = isProviderFormSupported(providerCode);
  const credFields = useMemo(
    () => credentialFields(providerCode),
    [providerCode],
  );
  const metaFields = useMemo(
    () => originMetadataFields(providerCode),
    [providerCode],
  );
  const orderFields = useMemo(
    () => configFields(providerCode).filter((f) => f.section === 'order'),
    [providerCode],
  );
  const httpFields = useMemo(
    () => configFields(providerCode).filter((f) => f.section === 'http'),
    [providerCode],
  );

  function handleProviderChange(code) {
    setProviderCode(code);
    setSubmitAttempted(false);
    setCredentials({});
    // Config / origin / metadata are provider-specific — re-seed them for
    // the new provider. Pre-fill the country code (RU marketplace default).
    const fresh = splitConfigToForm(
      { default_origin: { country_code: 'RU' } },
      code,
    );
    setTestMode(fresh.testMode);
    setConfigValues(fresh.configValues);
    setOriginValues(fresh.originValues);
    setMetadataValues(fresh.metadataValues);
    setAdvancedText(fresh.advancedText);
    setAdvancedOpen(false);
    originExtraRef.current = fresh.originExtra;
    metadataExtraRef.current = fresh.metadataExtra;
  }

  // Format / consistency errors — always evaluated, block submit regardless
  // of whether the operator has attempted it yet.
  const formatErrors = useMemo(() => {
    const config = {};
    for (const field of configFields(providerCode)) {
      if (field.type !== 'number') continue;
      const value = configValues[field.key];
      if (isFilled(value) && !Number.isFinite(Number(value))) {
        config[field.key] = 'Введите число';
      }
    }
    const origin = {};
    for (const field of originFields(providerCode)) {
      if (field.type !== 'number') continue;
      const value = originValues[field.key];
      if (isFilled(value) && !Number.isFinite(Number(value))) {
        origin[field.key] = 'Введите число';
      }
    }
    let advanced = '';
    if (isFilled(advancedText)) {
      try {
        const parsed = JSON.parse(advancedText);
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          advanced = 'JSON должен быть объектом';
        }
      } catch {
        advanced = 'Некорректный JSON';
      }
    }
    return { config, origin, advanced };
  }, [providerCode, configValues, originValues, advancedText]);

  const credsRequired = isEdit ? changeCredentials : true;
  const credsOk =
    !credsRequired ||
    (credFields.length > 0 &&
      credFields.every((field) => isFilled(credentials[field.key])));
  const requiredMetaOk = metaFields
    .filter((field) => field.required)
    .every((field) => isFilled(metadataValues[field.key]));

  const requiredOk =
    supported &&
    isFilled(name) &&
    credsOk &&
    isFilled(originValues.country_code) &&
    isFilled(originValues.city) &&
    requiredMetaOk;

  const hasFormatErrors =
    Object.keys(formatErrors.config).length > 0 ||
    Object.keys(formatErrors.origin).length > 0 ||
    Boolean(formatErrors.advanced);

  const canSubmit = requiredOk && !hasFormatErrors && !mutation.isPending;

  // Required-but-empty messages — surfaced only after a submit attempt, so a
  // fresh form is never a wall of red.
  const requiredErrors = useMemo(() => {
    if (!submitAttempted) {
      return { name: undefined, credentials: {}, origin: {}, metadata: {} };
    }
    const credentialsErr = {};
    if (credsRequired) {
      for (const field of credFields) {
        if (!isFilled(credentials[field.key])) {
          credentialsErr[field.key] = REQUIRED;
        }
      }
    }
    const originErr = {};
    for (const field of originFields(providerCode)) {
      if (field.required && !isFilled(originValues[field.key])) {
        originErr[field.key] = REQUIRED;
      }
    }
    const metadataErr = {};
    for (const field of metaFields) {
      if (field.required && !isFilled(metadataValues[field.key])) {
        metadataErr[field.key] = REQUIRED;
      }
    }
    return {
      name: isFilled(name) ? undefined : REQUIRED,
      credentials: credentialsErr,
      origin: originErr,
      metadata: metadataErr,
    };
  }, [
    submitAttempted,
    credsRequired,
    credFields,
    credentials,
    providerCode,
    originValues,
    metaFields,
    metadataValues,
    name,
  ]);

  // Format errors win over "required" — typing something wrong is more
  // specific feedback than typing nothing.
  const originErrors = { ...requiredErrors.origin, ...formatErrors.origin };

  function patchOrigin(key, value) {
    setOriginValues((prev) => ({ ...prev, [key]: value }));
  }
  function patchMetadata(key, value) {
    setMetadataValues((prev) => ({ ...prev, [key]: value }));
  }
  function patchConfig(key, value) {
    setConfigValues((prev) => ({ ...prev, [key]: value }));
  }
  function patchCredential(key, value) {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  }
  // Toggling "replace credentials" off clears anything typed — an aborted
  // change must not linger and overwrite the live keys on submit.
  function handleChangeCredentials(next) {
    setChangeCredentials(next);
    if (!next) setCredentials({});
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!canSubmit) {
      setSubmitAttempted(true);
      return;
    }

    const config = buildConfigFromForm(
      {
        testMode,
        configValues,
        originValues,
        metadataValues,
        originExtra: originExtraRef.current,
        metadataExtra: metadataExtraRef.current,
        advancedText,
      },
      providerCode,
    );

    let payload;
    if (isEdit) {
      payload = { name: name.trim(), config, replaceConfig: true };
      if (changeCredentials) {
        payload.credentials = buildCredentials(credFields, credentials);
      }
    } else {
      payload = {
        providerCode,
        name: name.trim(),
        credentials: buildCredentials(credFields, credentials),
        config,
        isActive,
      };
    }

    mutation.mutate(payload, {
      onSuccess: async () => {
        await refreshRegistry(
          isEdit ? 'Изменения сохранены' : 'Провайдер создан',
        );
        onClose();
      },
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title={isEdit ? 'Редактировать провайдера' : 'Добавить провайдера'}
    >
      {isEdit && existingPending ? (
        <EditSkeleton />
      ) : (
        <form
          onSubmit={handleSubmit}
          className="mt-4 flex max-h-[68vh] flex-col"
        >
          <div className="flex-1 space-y-6 overflow-y-auto pr-1">
            <Section title="Провайдер">
              {isEdit ? (
                <div className="border-app-border flex items-center gap-3 rounded-lg border px-3 py-2.5">
                  <ProviderLogo
                    code={providerCode}
                    className="h-8 w-8 rounded-lg"
                  />
                  <ProviderName
                    code={providerCode}
                    className="text-app-text-dark text-sm font-medium"
                    logoClassName="h-5"
                  />
                </div>
              ) : (
                <>
                  <ProviderPicker
                    value={providerCode}
                    onChange={handleProviderChange}
                    disabled={mutation.isPending}
                  />
                  {providerCode && PROVIDER_HINTS[providerCode] && (
                    <p className="text-app-muted text-xs">
                      {PROVIDER_HINTS[providerCode]}
                    </p>
                  )}
                </>
              )}
            </Section>

            {providerCode && !supported && (
              <ProviderFormStub code={providerCode} />
            )}

            {providerCode && supported && (
              <>
                <Section title="Учётная запись">
                  <FormField
                    label="Название"
                    required
                    placeholder="Например: Yandex Delivery (production)"
                    value={name}
                    error={requiredErrors.name}
                    disabled={mutation.isPending}
                    onChange={setName}
                  />
                  {!isEdit && (
                    <CheckboxRow
                      label="Активен"
                      hint="У провайдера может быть только один активный аккаунт. Для ротации ключей создайте новый аккаунт неактивным, затем переключите."
                      checked={isActive}
                      onChange={setIsActive}
                      disabled={mutation.isPending}
                    />
                  )}
                </Section>

                <Section
                  title="Учётные данные"
                  description={
                    isEdit
                      ? 'Поле пустое — токен не меняется. Введите новый — он заменит текущий.'
                      : 'OAuth-токен из бизнес-кабинета Яндекс Доставки.'
                  }
                >
                  <CredentialsSection
                    providerCode={providerCode}
                    fingerprints={existing?.credentialFingerprints}
                    values={credentials}
                    onChange={patchCredential}
                    isEdit={isEdit}
                    changing={changeCredentials}
                    onChangingChange={handleChangeCredentials}
                    errors={requiredErrors.credentials}
                    disabled={mutation.isPending}
                  />
                </Section>

                <Section title="Режим">
                  <CheckboxRow
                    label="Тестовый режим"
                    hint="Переключает запросы на тестовый контур Яндекса. В sandbox принимаются только адреса Москвы."
                    checked={testMode}
                    onChange={setTestMode}
                    disabled={mutation.isPending}
                  />
                </Section>

                <Section
                  title="Склад-отправитель"
                  description="Код страны, город и ID склада обязательны — без них backend вернёт PROVIDER_UNAVAILABLE при расчёте доставки."
                >
                  <DefaultOriginFields
                    providerCode={providerCode}
                    values={originValues}
                    metadata={metadataValues}
                    errors={originErrors}
                    metadataErrors={requiredErrors.metadata}
                    onChangeValue={patchOrigin}
                    onChangeMetadata={patchMetadata}
                    disabled={mutation.isPending}
                  />
                </Section>

                {orderFields.length > 0 && (
                  <Section
                    title="Параметры заказа"
                    description="Значения по умолчанию для создаваемых отгрузок — все поля опциональны."
                  >
                    <ConfigFieldGrid
                      fields={orderFields}
                      values={configValues}
                      errors={formatErrors.config}
                      onChange={patchConfig}
                      disabled={mutation.isPending}
                    />
                  </Section>
                )}

                {httpFields.length > 0 && (
                  <CollapsibleSection
                    title="HTTP-клиент"
                    description="Тайм-аут и повторы запросов к API провайдера. По умолчанию 30 сек / 3 повтора."
                  >
                    <ConfigFieldGrid
                      fields={httpFields}
                      values={configValues}
                      errors={formatErrors.config}
                      onChange={patchConfig}
                      disabled={mutation.isPending}
                    />
                  </CollapsibleSection>
                )}

                <AdvancedConfigField
                  value={advancedText}
                  error={formatErrors.advanced}
                  open={advancedOpen}
                  onToggle={() => setAdvancedOpen((prev) => !prev)}
                  onChange={setAdvancedText}
                  disabled={mutation.isPending}
                />
              </>
            )}

            {mutation.error && (
              <div
                role="alert"
                className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {mutation.error.message}
              </div>
            )}
          </div>

          <div className="border-app-border mt-4 flex shrink-0 items-center justify-end gap-3 border-t pt-3">
            {supported &&
              submitAttempted &&
              !canSubmit &&
              !mutation.isPending && (
                <p className="text-app-danger mr-auto text-xs">
                  Заполните обязательные поля и проверьте формат значений.
                </p>
              )}
            <button
              type="button"
              onClick={onClose}
              disabled={mutation.isPending}
              className="text-app-muted hover:text-app-text-dark px-3 py-2 text-sm font-medium"
            >
              {supported ? 'Отмена' : 'Закрыть'}
            </button>
            {supported && (
              <button
                type="submit"
                disabled={mutation.isPending}
                className="bg-app-text-dark rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {mutation.isPending
                  ? 'Сохраняем…'
                  : isEdit
                    ? 'Сохранить'
                    : 'Создать провайдера'}
              </button>
            )}
          </div>
        </form>
      )}
    </Modal>
  );
}
