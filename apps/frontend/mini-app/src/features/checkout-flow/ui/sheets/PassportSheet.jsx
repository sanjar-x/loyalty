'use client';

import { useMemo } from 'react';

import BottomSheet from '@/shared/ui/BottomSheet';
import { useTelegram } from '@/entities/user';

// Cross-feature import accepted: the passport-form feature owns the
// `<PassportPicker />` UX block. Cart-flow and buy-now compose the
// same picker so list+create stays uniform across both checkout paths.
// PHASE-9-TODO.md tracks the warn.
// eslint-disable-next-line no-restricted-imports
import { PassportPicker } from '@/features/passport-form';

/**
 * Cart-flow Passport sheet — replaces the legacy CustomsSheet
 * (Sprint 1.5 Part 2 / ADR-011). Opens from `CheckoutTiles` on the
 * «Паспорт для таможни» tile (only rendered when the cart has any
 * cross-border item).
 *
 * Props:
 *   • open                  — controlled by the parent page
 *   • onClose               — called on close button / backdrop tap
 *   • selectedId            — currently resolved passportId (controls
 *                             which card is highlighted)
 *   • onResolved(passportId) — called after the customer picked an
 *                              existing passport OR a new one was
 *                              created via the inline form. Parent
 *                              writes it to `useCheckoutStore.passportId`
 *                              and closes the sheet.
 */
export default function PassportSheet({ open, onClose, selectedId, onResolved }) {
  const tg = useTelegram();
  const prefillSource = useMemo(() => {
    if (!tg?.user) return null;
    return { first_name: tg.user.first_name, last_name: tg.user.last_name };
  }, [tg?.user]);

  const handleResolved = (passportId) => {
    onResolved?.(passportId);
    onClose?.();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Паспорт для таможни">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingBottom: 12 }}>
        <div style={{ fontSize: 12, color: 'rgba(17,17,17,0.6)', lineHeight: 1.35 }}>
          В корзине есть товары из-за рубежа — для таможенной декларации нужен паспорт получателя.
          Один паспорт можно использовать для нескольких получателей и заказов.
        </div>
        <PassportPicker
          selectedId={selectedId}
          onPick={handleResolved}
          onCreated={handleResolved}
          prefillSource={prefillSource}
          testIdPrefix="cart-passport"
        />
      </div>
    </BottomSheet>
  );
}
