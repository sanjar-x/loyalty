'use client';

import { useEffect, useMemo, useState } from 'react';

import { useCreateRecipientMutation, useListMyRecipientsQuery } from '@/entities/recipient';
import { useTelegram } from '@/entities/user';
import { humanizeApiError, normalizeApiError } from '@/shared/api/errors';
import { toast } from '@/shared/ui/Toaster';
import FormField from '@/shared/ui/FormField';
import {
  PHONE_FORMATS,
  SUPPORTED_PHONE_COUNTRIES,
  formatPhone,
  normalizePhoneDigits,
} from '@/shared/lib/phone';

// Cross-feature import accepted: one-tap Buy Now UX needs the inline
// recipient form. ESLint cross-feature warn documented in PHASE-9-TODO.md;
// revisit when the god-component refactor lands.
// eslint-disable-next-line no-restricted-imports
import { useRecipientForm } from '@/features/recipient-form';

import { useBuyNowStore } from '../../model/useBuyNowCheckout';
import styles from '../BuyNowSheet.module.css';

/**
 * Step 2 — Recipient (shipping coordinates only).
 *
 * ADR-010 I2: backend never exposes a combined `recipient + order`
 * endpoint, so this step MUST resolve a `recipientId` before
 * ConfirmStep can POST /orders/buy-now. Two paths:
 *
 *   pick  — choose from `useListMyRecipientsQuery` items
 *   new   — inline form ► POST /recipients ► auto-select created id
 *
 * Post-ADR-011: customs documents (passport, INN, dates) have moved to
 * the independent Passport bounded context. RecipientStep now collects
 * only shipping coordinates (full name in RU + Latin, phone, email) —
 * the same payload the backend's reduced `CreateRecipientRequest`
 * accepts. The customs collection lives in `PassportStep`, rendered
 * only for cross-border SKUs by the FSM.
 *
 * The Latin name is required by the new schema (used on courier
 * documents); we keep it next to the RU field rather than relying on a
 * client-side transliterator so the customer can correct spelling.
 *
 * UX (per product Q answer): if the existing recipient roster is empty,
 * jump straight into `new` mode — no intermediate empty-state screen.
 */

const RU_TO_LAT = {
  а: 'a',
  б: 'b',
  в: 'v',
  г: 'g',
  д: 'd',
  е: 'e',
  ё: 'e',
  ж: 'zh',
  з: 'z',
  и: 'i',
  й: 'i',
  к: 'k',
  л: 'l',
  м: 'm',
  н: 'n',
  о: 'o',
  п: 'p',
  р: 'r',
  с: 's',
  т: 't',
  у: 'u',
  ф: 'f',
  х: 'kh',
  ц: 'ts',
  ч: 'ch',
  ш: 'sh',
  щ: 'shch',
  ъ: '',
  ы: 'y',
  ь: '',
  э: 'e',
  ю: 'iu',
  я: 'ia',
};

function transliterateRuToLat(input) {
  if (typeof input !== 'string') return '';
  let out = '';
  for (const ch of input) {
    const lower = ch.toLowerCase();
    const mapped = RU_TO_LAT[lower];
    if (mapped == null) {
      out += ch;
      continue;
    }
    out += ch === lower ? mapped : mapped.charAt(0).toUpperCase() + mapped.slice(1);
  }
  return out;
}

export default function RecipientStep() {
  const recipientId = useBuyNowStore((s) => s.recipientId);
  const setRecipientId = useBuyNowStore((s) => s.setRecipientId);
  const nextStep = useBuyNowStore((s) => s.nextStep);

  const { data, isLoading, isError, refetch } = useListMyRecipientsQuery({ limit: 50 });
  const items = useMemo(() => (Array.isArray(data?.items) ? data.items : []), [data]);
  const isEmptyList = !isLoading && items.length === 0;

  const [mode, setMode] = useState(isEmptyList ? 'new' : 'pick');
  useEffect(() => {
    if (isEmptyList) setMode('new');
  }, [isEmptyList]);

  return (
    <div className={styles.stepRoot}>
      <div className={styles.stepTitle}>2. Получатель</div>

      {isLoading ? (
        <div className={styles.placeholder}>Загружаем получателей…</div>
      ) : isError ? (
        <div className={styles.placeholder}>
          Не удалось загрузить получателей.
          <br />
          <button type="button" className={styles.secondaryBtn} onClick={() => refetch?.()}>
            Повторить
          </button>
        </div>
      ) : mode === 'pick' ? (
        <PickList
          items={items}
          recipientId={recipientId}
          onPick={(id) => {
            setRecipientId(id);
            nextStep();
          }}
          onAddNew={() => setMode('new')}
        />
      ) : (
        <NewRecipientForm
          canGoBack={!isEmptyList}
          onCancel={() => setMode('pick')}
          onSaved={(id) => {
            setRecipientId(id);
            nextStep();
          }}
        />
      )}
    </div>
  );
}

/* ─────────────────────────────  Pick existing  ──────────────────────── */

function PickList({ items, recipientId, onPick, onAddNew }) {
  return (
    <>
      {items.map((r) => {
        const selected = recipientId === r.recipientId;
        return (
          <button
            key={r.recipientId}
            type="button"
            className={styles.secondaryBtn}
            onClick={() => onPick(r.recipientId)}
            aria-pressed={selected}
            data-testid={`buy-now-recipient-card-${r.recipientId}`}
            style={
              selected ? { borderColor: '#111', background: 'rgba(17,17,17,0.05)' } : undefined
            }
          >
            <div>{r.fullNameRu || r.fullNameLat || 'Без имени'}</div>
            {r.phone ? <div style={{ opacity: 0.6, fontSize: 12 }}>{r.phone}</div> : null}
          </button>
        );
      })}
      <button
        type="button"
        className={styles.primaryBtn}
        onClick={onAddNew}
        data-testid="buy-now-recipient-add"
      >
        + Новый получатель
      </button>
    </>
  );
}

/* ─────────────────────────────  New recipient form  ─────────────────── */

function NewRecipientForm({ canGoBack, onCancel, onSaved }) {
  const tg = useTelegram();
  const prefillSource = useMemo(() => {
    if (!tg?.user) return null;
    return { first_name: tg.user.first_name, last_name: tg.user.last_name };
  }, [tg?.user]);

  const recipientForm = useRecipientForm({
    initialValue: null,
    prefillSource,
    onSave: () => {},
  });

  // Latin name lives in local state because `useRecipientForm` (shared
  // with cart-flow) doesn't carry that field. Recipient must always
  // send `fullNameLat` post-ADR-011; we seed it from the Russian input
  // via transliteration so the customer can correct it.
  const [fullNameLat, setFullNameLat] = useState('');
  const [latTouched, setLatTouched] = useState(false);
  const [latError, setLatError] = useState(null);

  useEffect(() => {
    if (latTouched) return;
    const seed = transliterateRuToLat(recipientForm.draft.fullName || '').trim();
    setFullNameLat(seed);
  }, [recipientForm.draft.fullName, latTouched]);

  const [createRecipient, createState] = useCreateRecipientMutation();

  const submit = async () => {
    const baseOk = recipientForm.handleSubmit();
    const lat = fullNameLat.trim();
    const latOk = /^[A-Za-z' .\-]+$/.test(lat) && lat.split(/\s+/).filter(Boolean).length >= 2;
    if (!latOk) {
      setLatError('Минимум имя и фамилия латиницей');
    } else {
      setLatError(null);
    }
    if (!baseOk || !latOk) return;

    const country = recipientForm.draft.country || 'RU';
    const phoneFormat = PHONE_FORMATS[country] || PHONE_FORMATS.RU;
    try {
      const body = {
        fullNameRu: recipientForm.draft.fullName.trim(),
        fullNameLat: lat,
        phone: `${phoneFormat.prefix}${recipientForm.draft.phoneDigits}`,
        email: recipientForm.draft.email.trim(),
      };
      const resp = await createRecipient(body).unwrap();
      const id = resp?.recipientId;
      if (!id) {
        toast.error('Не удалось сохранить получателя');
        return;
      }
      onSaved(id);
    } catch (err) {
      const norm = normalizeApiError(err);
      const message =
        norm.code && norm.code !== ''
          ? `${norm.code}: ${norm.message || humanizeApiError(err)}`
          : humanizeApiError(err, 'Не удалось сохранить получателя');
      toast.error(message);
    }
  };

  const phoneFmt = PHONE_FORMATS[recipientForm.draft.country] || PHONE_FORMATS.RU;
  const submitting = createState.isLoading;

  return (
    <div className={styles.stepRoot}>
      <RecipientContactFields
        form={recipientForm}
        phoneFmt={phoneFmt}
        latValue={fullNameLat}
        latError={latError}
        onLatChange={(value) => {
          setLatTouched(true);
          setFullNameLat(value);
          if (latError) setLatError(null);
        }}
      />

      <div style={{ display: 'flex', gap: 8 }}>
        {canGoBack ? (
          <button type="button" className={styles.secondaryBtn} onClick={onCancel}>
            Назад
          </button>
        ) : null}
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={submit}
          disabled={submitting}
          aria-busy={submitting}
          data-testid="buy-now-recipient-save"
          style={{ flex: 1 }}
        >
          {submitting ? 'Сохраняем…' : 'Сохранить и продолжить'}
        </button>
      </div>
    </div>
  );
}

function RecipientContactFields({ form, phoneFmt, latValue, latError, onLatChange }) {
  const { draft, setField, errors, submitAttempted } = form;
  const fieldError = (field, requiredText, invalidText) => {
    if (!submitAttempted) return null;
    const code = errors[field];
    if (code === 'required') return requiredText;
    if (code === 'invalid') return invalidText;
    return null;
  };

  const onCountryChange = (e) => {
    const next = e.target.value;
    const nextFmt = PHONE_FORMATS[next] || PHONE_FORMATS.RU;
    setField('country', next);
    setField('phoneDigits', (draft.phoneDigits || '').slice(0, nextFmt.lenAfter));
  };

  const countrySelect = (
    <select
      aria-label="Код страны"
      value={draft.country}
      onChange={onCountryChange}
      style={{ border: 'none', background: 'transparent' }}
    >
      {SUPPORTED_PHONE_COUNTRIES.map((c) => (
        <option key={c} value={c}>
          {c}
        </option>
      ))}
    </select>
  );

  return (
    <div className={styles.stepRoot}>
      <FormField
        label="ФИО"
        value={draft.fullName}
        onChange={(e) => setField('fullName', e.target.value)}
        error={fieldError('fullName', 'Заполните ФИО', 'Минимум имя и фамилия')}
        data-testid="buy-now-recipient-name-ru"
      />
      <FormField
        label="ФИО латиницей (для курьерки)"
        value={latValue}
        onChange={(e) => onLatChange(e.target.value)}
        error={latError}
        data-testid="buy-now-recipient-name-lat"
      />
      <FormField
        label="Телефон"
        value={formatPhone(draft.phoneDigits, draft.country)}
        onChange={(e) =>
          setField('phoneDigits', normalizePhoneDigits(e.target.value, draft.country))
        }
        error={fieldError('phoneDigits', 'Заполните телефон', `Формат: ${phoneFmt.placeholder}`)}
        type="tel"
        inputMode="tel"
        rightSlot={countrySelect}
        data-testid="buy-now-recipient-phone"
      />
      <FormField
        label="Email"
        value={draft.email}
        onChange={(e) => setField('email', e.target.value)}
        error={fieldError('email', 'Заполните email', 'Неверный формат')}
        type="email"
        inputMode="email"
        data-testid="buy-now-recipient-email"
      />
    </div>
  );
}
