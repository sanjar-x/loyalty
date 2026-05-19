'use client';

import { useEffect, useState } from 'react';

import { PassportCard, usePassportSelection } from '@/entities/passport';

import PassportForm from './PassportForm';
import styles from './PassportPicker.module.css';

/**
 * Reusable picker composer for the Passport bounded context (ADR-011).
 *
 * Composes:
 *   • `usePassportSelection`         — non-archived passports roster
 *   • `<PassportCard />`             — read-only list items
 *   • `<PassportForm />`             — inline create-new form
 *
 * Used both by buy-now PassportStep and cart-flow PassportSheet. Empty
 * roster jumps straight into the new-passport form (no intermediate
 * empty-state screen — matches the recipient-form UX answer).
 *
 * Props:
 *   • selectedId         — currently selected passport id (controlled).
 *                          The picker highlights the matching card.
 *   • onPick(passportId) — called when the customer picks an existing
 *                          passport. Caller decides what to do next
 *                          (advance FSM, close sheet, etc.).
 *   • onCreated(passportId)
 *                        — called after a fresh passport was POSTed
 *                          successfully via PassportForm. Caller is
 *                          responsible for store + FSM updates.
 *   • prefillSource      — optional Telegram user shape passed to
 *                          PassportForm so the new-mode RU name field
 *                          can be seeded.
 *   • onBack             — optional «Назад» button rendered in the pick
 *                          mode (used by buy-now PassportStep to return
 *                          to the recipient step).
 *   • testIdPrefix       — `data-testid` namespace; defaults to
 *                          'passport-picker'.
 *   • backLabel          — label for the back button in pick mode;
 *                          defaults to 'Назад'.
 *   • cancelNewLabel     — label for the cancel button inside the
 *                          new-mode form (only shown when the roster is
 *                          non-empty so the customer can flip back to
 *                          the list); defaults to 'К списку'.
 *
 * NOTE: PassportPicker stays in features/passport-form (not entities)
 * because it composes a feature (the create form). Per FSD, an entity
 * must not consume a feature — keeping the picker here preserves the
 * dependency direction.
 */
export default function PassportPicker({
  selectedId = null,
  onPick,
  onCreated,
  prefillSource,
  onBack,
  testIdPrefix = 'passport-picker',
  backLabel = 'Назад',
  cancelNewLabel = 'К списку',
}) {
  const { items, isLoading, isError, refetch } = usePassportSelection();
  const isEmptyList = !isLoading && items.length === 0;

  const [mode, setMode] = useState(isEmptyList ? 'new' : 'pick');
  useEffect(() => {
    if (isEmptyList) setMode('new');
  }, [isEmptyList]);

  if (isLoading) {
    return <div className={styles.placeholder}>Загружаем паспорта…</div>;
  }

  if (isError) {
    return (
      <div className={styles.placeholder}>
        Не удалось загрузить паспорта.
        <br />
        <button type="button" className={styles.secondaryBtn} onClick={() => refetch?.()}>
          Повторить
        </button>
      </div>
    );
  }

  if (mode === 'pick') {
    return (
      <div className={styles.root}>
        {items.map((p) => (
          <PassportCard
            key={p.passportId}
            passport={p}
            selected={selectedId === p.passportId}
            onSelect={() => onPick?.(p.passportId)}
            testId={`${testIdPrefix}-card-${p.passportId}`}
          />
        ))}
        <button
          type="button"
          className={styles.primaryBtn}
          onClick={() => setMode('new')}
          data-testid={`${testIdPrefix}-add`}
        >
          + Новый паспорт
        </button>
        {onBack ? (
          <button type="button" className={styles.secondaryBtn} onClick={onBack}>
            {backLabel}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <PassportForm
      prefillSource={prefillSource}
      onSuccess={onCreated}
      onCancel={isEmptyList ? undefined : () => setMode('pick')}
      cancelLabel={cancelNewLabel}
      testId={`${testIdPrefix}-form`}
    />
  );
}
