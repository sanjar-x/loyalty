'use client';

import { useState } from 'react';

import { CopyMark } from '@/shared/ui/CopyMark';
import { cn } from '@/shared/lib/utils';
import dayjs from '@/shared/lib/dayjs';

import { formatInn, maskEmail, maskPassport, maskPhone } from '../lib/mask';

/**
 * Customs PII for the order's recipient — frozen at checkout, surfaced
 * here so admins can verify it against the China-side procurement
 * invoice. Passport / phone / email are masked by default; INN is shown
 * raw because the customs declaration legally requires full precision.
 *
 * The "Показать полностью" toggle reveals the rest, gated behind an
 * explicit click + an `aria-pressed` button so screen-recordings and
 * casual onlookers don't see PII unless the operator deliberately
 * unmasked it.
 */
export function RecipientSnapshotPanel({ snapshot }) {
  const [revealed, setRevealed] = useState(false);

  if (!snapshot) {
    return (
      <article
        className="border-app-border rounded-2xl border border-dashed p-5"
        data-testid="recipient-snapshot-empty"
      >
        <p className="text-app-muted text-sm">
          Получатель ещё не привязан к заказу.
        </p>
      </article>
    );
  }

  const passportFull = `${snapshot.passportSerial} ${snapshot.passportNumber}`;
  const passportDisplay = revealed
    ? passportFull
    : maskPassport(snapshot.passportSerial, snapshot.passportNumber);
  const phoneDisplay = revealed ? snapshot.phone : maskPhone(snapshot.phone);
  const emailDisplay = revealed ? snapshot.email : maskEmail(snapshot.email);

  return (
    <article
      className="bg-app-card rounded-2xl p-5"
      aria-label="Получатель — данные для таможни"
    >
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-app-text-dark text-lg font-semibold">Получатель</h2>
        <button
          type="button"
          onClick={() => setRevealed((prev) => !prev)}
          aria-pressed={revealed}
          className={cn(
            'inline-flex h-8 items-center rounded-lg border px-2.5 text-xs font-medium transition-colors',
            revealed
              ? 'border-app-danger bg-app-danger/10 text-app-danger'
              : 'border-app-border text-app-muted hover:border-app-text-dark hover:text-app-text-dark',
          )}
        >
          {revealed ? 'Скрыть полностью' : 'Показать полностью'}
        </button>
      </header>

      <dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
        <Field term="ФИО (русский)" value={snapshot.fullNameRu} copy />
        <Field term="ФИО (латиница)" value={snapshot.fullNameLat} copy />
        <Field
          term="Телефон"
          value={phoneDisplay}
          rawValue={snapshot.phone}
          copy
          aria={
            revealed
              ? 'Телефон получателя'
              : 'Телефон получателя, замаскирован для безопасности'
          }
        />
        <Field
          term="Email"
          value={emailDisplay}
          rawValue={snapshot.email}
          copy
          aria={
            revealed
              ? 'Email получателя'
              : 'Email получателя, замаскирован для безопасности'
          }
        />
        <Field
          term="Паспорт"
          value={passportDisplay}
          rawValue={passportFull}
          copy
          aria={
            revealed
              ? 'Паспорт получателя'
              : 'Паспорт получателя, замаскирован для безопасности'
          }
        />
        <Field
          term="Выдан"
          value={
            snapshot.passportIssueDate
              ? dayjs(snapshot.passportIssueDate).format('LL')
              : '—'
          }
        />
        <Field
          term="Дата рождения"
          value={
            snapshot.birthDate ? dayjs(snapshot.birthDate).format('LL') : '—'
          }
        />
        <Field
          term="ИНН"
          value={formatInn(snapshot.inn)}
          copy
          aria="ИНН получателя, не маскируется — нужен для таможенной декларации"
        />
      </dl>
    </article>
  );
}

function Field({ term, value, rawValue, copy = false, aria }) {
  const display = value ?? '—';
  return (
    <div className="border-app-border/60 rounded-xl border bg-white/60 p-3">
      <dt className="text-app-muted mb-1 text-xs font-medium tracking-wide uppercase">
        {term}
      </dt>
      <dd
        className="text-app-text-dark inline-flex items-center gap-2 text-sm font-medium"
        aria-label={aria || term}
      >
        <span className="font-mono">{display}</span>
        {copy ? <CopyMark text={String(rawValue ?? display)} /> : null}
      </dd>
    </div>
  );
}
