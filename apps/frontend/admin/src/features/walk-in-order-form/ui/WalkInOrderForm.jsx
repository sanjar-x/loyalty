'use client';

import Link from 'next/link';
import { useState } from 'react';

import { cn } from '@/shared/lib/utils';

import {
  validateEmail,
  validateInn,
  validateIsoDate,
  validateItemsLength,
  validateNonEmptyString,
  validatePassportNumber,
  validatePassportSerial,
  validatePhone,
  validatePriceOverride,
  validateQuantity,
} from '../lib/validators';
import { useSubmitWalkInOrder } from '../model/useSubmitWalkInOrder';
import { useWalkInOrderForm } from '../model/useWalkInOrderForm';
import { CustomerProfileSection } from './sections/CustomerProfileSection';
import { ItemsSection } from './sections/ItemsSection';
import { OfflinePaymentSection } from './sections/OfflinePaymentSection';
import { PickupPointSection } from './sections/PickupPointSection';
import { RecipientSnapshotSection } from './sections/RecipientSnapshotSection';

// Aggregate validity check — submit button only enables when every
// required field passes its client-side validator. The submit handler
// also force-touches all fields so a "click straight to submit" surfaces
// the same errors as blur-by-blur navigation.
function computeFormValidity(state) {
  const { profile, recipient, items, payment } = state;

  if (!validateNonEmptyString(profile.fullName)) return false;
  if (!validatePhone(profile.phone)) return false;
  if (profile.email.length > 0 && !validateEmail(profile.email)) return false;

  if (!validateNonEmptyString(recipient.fullNameRu)) return false;
  if (!validateNonEmptyString(recipient.fullNameLat)) return false;
  if (!validatePhone(recipient.phone)) return false;
  if (!validateEmail(recipient.email)) return false;
  if (!validatePassportSerial(recipient.passportSerial)) return false;
  if (!validatePassportNumber(recipient.passportNumber)) return false;
  if (!validateIsoDate(recipient.passportIssueDate)) return false;
  if (!validateIsoDate(recipient.birthDate)) return false;
  if (!validateInn(recipient.inn)) return false;

  if (!validateItemsLength(items)) return false;
  for (const it of items) {
    if (!validateQuantity(it.quantity)) return false;
    if (it.unitPriceOverrideAmount != null) {
      const check = validatePriceOverride({
        override: it.unitPriceOverrideAmount,
        basePrice: it.sku?.sellingPriceAmount ?? null,
      });
      if (!check.ok) return false;
      if (!validateNonEmptyString(it.overrideReason)) return false;
    }
  }

  if (!state.pickupCarrier || !state.pickupPointId) return false;

  if (!validateNonEmptyString(payment.reference, { maxLength: 128 }))
    return false;

  return true;
}

// All `touched` flag names used across sections. Listing them here in one
// place lets the submit handler mark everything as touched in a single
// pass without having to know about each section's internal flag scheme.
const ALL_FIELDS = [
  'profileFullName',
  'profilePhone',
  'profileEmail',
  'recipientFullNameRu',
  'recipientFullNameLat',
  'recipientPhone',
  'recipientEmail',
  'recipientPassportSerial',
  'recipientPassportNumber',
  'recipientPassportIssueDate',
  'recipientBirthDate',
  'recipientInn',
  'paymentReference',
];

export function WalkInOrderForm() {
  const form = useWalkInOrderForm();
  const [touched, setTouched] = useState({});

  const submitState = useSubmitWalkInOrder({
    state: form.state,
    resetForm: form.resetForm,
  });

  const onTouch = (field) => setTouched((t) => ({ ...t, [field]: true }));
  const touchAll = () => {
    const all = {};
    for (const k of ALL_FIELDS) all[k] = true;
    setTouched(all);
  };

  const valid = computeFormValidity(form.state);

  function handleSubmit(e) {
    e.preventDefault();
    if (!valid) {
      touchAll();
      return;
    }
    submitState.submit();
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <header className="flex items-center justify-between">
        <div>
          <Link
            href="/admin/orders"
            className="text-app-muted hover:text-app-text text-sm"
          >
            ← Назад к списку заказов
          </Link>
          <h1 className="text-app-text mt-1 text-3xl font-bold">
            Создание walk-in заказа
          </h1>
        </div>
      </header>

      <CustomerProfileSection
        profile={form.state.profile}
        setProfileField={form.setProfileField}
        touched={touched}
        onTouch={onTouch}
      />

      <RecipientSnapshotSection
        recipient={form.state.recipient}
        setRecipientField={form.setRecipientField}
        touched={touched}
        onTouch={onTouch}
      />

      <ItemsSection
        items={form.state.items}
        addItem={form.addItem}
        removeItem={form.removeItem}
        updateItem={form.updateItem}
        deliveryAmount={form.state.deliveryAmount}
        setDeliveryAmount={form.setDeliveryAmount}
        itemErrors={submitState.itemErrors}
      />

      <PickupPointSection
        pickupCarrier={form.state.pickupCarrier}
        pickupPointId={form.state.pickupPointId}
        pickupPointLabel={form.state.pickupPointLabel}
        setPickup={form.setPickup}
      />

      <OfflinePaymentSection
        payment={form.state.payment}
        setPaymentField={form.setPaymentField}
        touched={touched}
        onTouch={onTouch}
      />

      {/*
        Render the global error above the footer (toasts auto-dismiss in
        ≤ 8s — codes like IDEMPOTENCY_KEY_CONFLICT need to stay visible
        until the admin fixes the underlying cause).
      */}
      {submitState.globalError && (
        <div
          role="alert"
          className="border-app-danger flex flex-col gap-2 rounded-2xl border bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          <p>{submitState.globalError.message}</p>
          {submitState.globalError.code === 'IDEMPOTENCY_KEY_CONFLICT' && (
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="self-start text-sm font-medium underline"
            >
              Обновить страницу
            </button>
          )}
        </div>
      )}

      <footer className="bg-app-panel border-app-border sticky bottom-0 flex items-center justify-end gap-3 rounded-3xl border p-4">
        <Link
          href="/admin/orders"
          className="text-app-text hover:bg-app-card rounded-2xl px-4 py-2 text-sm font-medium transition-colors"
        >
          Отменить
        </Link>
        <button
          type="submit"
          disabled={submitState.isPending}
          className={cn(
            'bg-app-text-dark rounded-2xl px-6 py-2 text-sm font-medium text-white transition-colors',
            submitState.isPending && 'cursor-not-allowed opacity-60',
            !valid && !submitState.isPending && 'opacity-80',
          )}
        >
          {submitState.isPending ? 'Создаём…' : 'Создать заказ'}
        </button>
      </footer>
    </form>
  );
}
