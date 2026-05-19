'use client';

import { OFFLINE_PAYMENT_METHODS } from '../../lib/constants';
import { validateNonEmptyString } from '../../lib/validators';
import { FormSection, TextField } from './FormSection';

// Offline payment fieldset. Reference is required by the backend — it's
// the audit anchor that proves money changed hands outside the gateway.
// `paidAt` defaults to "now" server-side when omitted; we keep it
// optional in the UI so a long-open form doesn't ship a stale timestamp.
export function OfflinePaymentSection({
  payment,
  setPaymentField,
  touched,
  onTouch,
}) {
  const selectedMethod = OFFLINE_PAYMENT_METHODS.find(
    (m) => m.value === payment.method,
  );

  return (
    <FormSection
      title="Оплата (offline)"
      description="Заказ создаётся сразу в статусе PAID. Платёжный шлюз НЕ вызывается."
    >
      <div className="bg-app-warningSoft text-app-text border-app-border rounded-2xl border px-4 py-3 text-sm">
        ⚠ Reference обязателен для бухгалтерской сверки. Без него заказ не
        сохранится.
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <label className="flex flex-col gap-1">
          <span className="text-app-muted text-xs font-medium">
            Способ оплаты <span className="text-app-danger">*</span>
          </span>
          <select
            value={payment.method}
            onChange={(e) => setPaymentField('method', e.target.value)}
            className="border-app-border bg-app-panel rounded-lg border px-3 py-2 text-sm outline-none"
          >
            {OFFLINE_PAYMENT_METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <TextField
          label="Документ / Reference"
          required
          name="paymentReference"
          value={payment.reference}
          onChange={(e) => setPaymentField('reference', e.target.value)}
          onBlur={() => onTouch('paymentReference')}
          helper={selectedMethod?.referenceHint}
          error={
            touched.paymentReference &&
            !validateNonEmptyString(payment.reference, { maxLength: 128 })
              ? 'Введите номер документа'
              : null
          }
        />
        <TextField
          label="Дата платежа"
          name="paymentPaidAt"
          type="datetime-local"
          value={payment.paidAt}
          onChange={(e) => setPaymentField('paidAt', e.target.value)}
          helper="Оставьте пустым — будет сохранено время отправки"
        />
      </div>
    </FormSection>
  );
}
