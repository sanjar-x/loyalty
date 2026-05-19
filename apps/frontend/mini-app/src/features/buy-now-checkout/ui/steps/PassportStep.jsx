'use client';

import { useMemo } from 'react';

import { useTelegram } from '@/entities/user';

// Cross-feature import accepted: the passport-form feature owns the
// `<PassportPicker />` UX block (list-then-form composer). ADR-011
// keeps the Passport bounded context independent — the feature owns
// its own CRUD + form composition. PHASE-9-TODO.md tracks the warn.
// eslint-disable-next-line no-restricted-imports
import { PassportPicker } from '@/features/passport-form';

import { useBuyNowStore } from '../../model/useBuyNowCheckout';
import styles from '../BuyNowSheet.module.css';

/**
 * Step 3 (cross-border only) — Passport.
 *
 * ADR-011: Passport is an independent bounded context, M:N with
 * Recipient via Order. The FSM in `useBuyNowCheckout` skips this step
 * entirely for LOCAL SKUs (`supplierType !== 'cross_border'`); when it
 * fires, the customer must resolve a `passportId` before PickupStep
 * can quote and ConfirmStep can POST /orders/buy-now.
 *
 * Step is a thin wrapper around `<PassportPicker />` from
 * features/passport-form — the same composer cart-flow's PassportSheet
 * reuses. The picker owns list+form orchestration so we only forward
 * the buy-now FSM updates here.
 *
 * Backend invariants enforced via the picker:
 *   • I3 (`passport.identity_id == order.identity_id`) — picker only
 *     ever lists /api/v1/passports/my (identity-scoped).
 *   • I4 (`passport.is_archived == false`) — `usePassportSelection`
 *     filters archived rows out client-side.
 */
export default function PassportStep() {
  const passportId = useBuyNowStore((s) => s.passportId);
  const setPassportId = useBuyNowStore((s) => s.setPassportId);
  const nextStep = useBuyNowStore((s) => s.nextStep);
  const prevStep = useBuyNowStore((s) => s.prevStep);

  const tg = useTelegram();
  const prefillSource = useMemo(() => {
    if (!tg?.user) return null;
    return { first_name: tg.user.first_name, last_name: tg.user.last_name };
  }, [tg?.user]);

  const advance = (id) => {
    setPassportId(id);
    nextStep();
  };

  return (
    <div className={styles.stepRoot} data-testid="buy-now-passport-step">
      <div className={styles.stepTitle}>3. Паспорт получателя</div>
      <div className={styles.stepHint}>
        Cross-border заказ — для таможенной декларации нужен паспорт получателя.
      </div>
      <PassportPicker
        selectedId={passportId}
        onPick={advance}
        onCreated={advance}
        prefillSource={prefillSource}
        onBack={prevStep}
        backLabel="Назад к получателю"
        testIdPrefix="buy-now-passport"
      />
    </div>
  );
}
