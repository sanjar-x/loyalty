'use client';

import { useState } from 'react';

import { cn, formatCurrency } from '@/shared/lib/utils';

import { MAX_PRICE_OVERRIDE_RATIO } from '../../lib/constants';
import { formatKopecksForInput, parseRublesToKopecks } from '../../lib/money';
import { validatePriceOverride } from '../../lib/validators';
import { SkuPickerModal } from '../SkuPickerModal';
import { FormSection, TextField } from './FormSection';

// Items section. Renders one ItemRow per chosen SKU + a "+ Добавить" CTA
// that opens the SkuPickerModal. Order total is computed locally so the
// admin sees the running sum (including delivery) as they edit.
//
// Per-line errors come from two places:
//   1) submit-time mapping in useSubmitWalkInOrder (itemErrors prop) —
//      these reflect what the backend rejected.
//   2) client-side override-out-of-range from validatePriceOverride —
//      prevents the user from typing 100x base and then waiting for a 422.
export function ItemsSection({
  items,
  addItem,
  removeItem,
  updateItem,
  deliveryAmount,
  setDeliveryAmount,
  itemErrors,
}) {
  const [pickerOpen, setPickerOpen] = useState(false);

  const subtotal = items.reduce((acc, it) => {
    const unit =
      it.unitPriceOverrideAmount != null
        ? it.unitPriceOverrideAmount
        : (it.sku?.sellingPriceAmount ?? 0);
    return acc + unit * (it.quantity ?? 1);
  }, 0);
  const total = subtotal + (deliveryAmount ?? 0);

  return (
    <FormSection
      title="Товары"
      description="Выберите SKU из каталога. Только активные и с рассчитанной ценой."
    >
      <div className="flex flex-col gap-3">
        {items.length === 0 && (
          <p className="text-app-muted bg-app-card rounded-2xl px-4 py-6 text-center text-sm">
            Ни одного товара не добавлено
          </p>
        )}

        {items.map((item) => (
          <ItemRow
            key={item.skuId}
            item={item}
            onChange={(patch) => updateItem(item.skuId, patch)}
            onRemove={() => removeItem(item.skuId)}
            serverError={itemErrors?.[item.skuId]?.message}
          />
        ))}

        <button
          type="button"
          onClick={() => setPickerOpen(true)}
          className="border-app-border text-app-text hover:bg-app-card self-start rounded-2xl border border-dashed px-4 py-2 text-sm font-medium transition-colors"
        >
          + Добавить товар
        </button>
      </div>

      <div className="border-app-border mt-2 flex flex-col gap-3 border-t pt-4 md:flex-row md:items-end md:justify-between">
        <TextField
          label="Доставка, ₽"
          name="deliveryAmount"
          inputMode="numeric"
          value={formatKopecksForInput(deliveryAmount)}
          onChange={(e) => {
            const next = parseRublesToKopecks(e.target.value);
            if (next == null) return;
            setDeliveryAmount(next);
          }}
          helper="Включается в итоговую сумму"
          className="md:w-60"
        />
        <div className="text-app-text text-right text-lg font-semibold">
          Итого: <span className="text-2xl">{formatCurrency(total / 100)}</span>
        </div>
      </div>

      <SkuPickerModal
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onSelect={addItem}
      />
    </FormSection>
  );
}

function ItemRow({ item, onChange, onRemove, serverError }) {
  const sku = item.sku ?? {};
  const overrideEnabled = item.unitPriceOverrideAmount != null;
  const basePrice = sku.sellingPriceAmount ?? 0;
  const unitPrice = overrideEnabled ? item.unitPriceOverrideAmount : basePrice;
  const lineTotal = unitPrice * (item.quantity ?? 1);

  const overrideCheck = overrideEnabled
    ? validatePriceOverride({
        override: item.unitPriceOverrideAmount,
        basePrice,
      })
    : { ok: true };
  const reasonMissing =
    overrideEnabled && !item.overrideReason?.trim()
      ? 'Укажите причину изменения цены'
      : null;

  return (
    <div
      className={cn(
        'border-app-border bg-app-panel flex flex-col gap-3 rounded-2xl border p-4',
        serverError && 'border-app-danger',
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="text-app-text text-sm font-medium">
            {sku.productName || '—'}{' '}
            {sku.variantLabel && (
              <span className="text-app-muted">— {sku.variantLabel}</span>
            )}
          </div>
          <div className="text-app-muted mt-0.5 font-mono text-xs">
            {sku.skuCode}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2">
            <span className="text-app-muted text-xs">Кол-во</span>
            <input
              type="number"
              min={1}
              max={99}
              value={item.quantity}
              onChange={(e) => {
                const n = Number.parseInt(e.target.value, 10);
                if (!Number.isFinite(n)) return;
                onChange({ quantity: Math.min(99, Math.max(1, n)) });
              }}
              className="border-app-border w-16 rounded-lg border px-2 py-1 text-center text-sm"
            />
          </label>
          <button
            type="button"
            onClick={onRemove}
            className="text-app-danger hover:bg-app-card rounded-lg px-2 py-1 text-xs"
            aria-label="Удалить позицию"
          >
            Удалить
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="text-app-muted flex items-center gap-2">
          <input
            type="checkbox"
            checked={overrideEnabled}
            onChange={(e) => {
              if (e.target.checked) {
                onChange({
                  unitPriceOverrideAmount: basePrice,
                  overrideReason: '',
                });
              } else {
                onChange({
                  unitPriceOverrideAmount: null,
                  overrideReason: '',
                });
              }
            }}
          />
          Изменить цену вручную
        </label>
        {!overrideEnabled && (
          <span className="text-app-muted">
            Базовая: {formatCurrency(basePrice / 100)}
          </span>
        )}
        {overrideEnabled && (
          <div className="flex flex-wrap items-end gap-2">
            <TextField
              label={`Новая цена, ₽ (макс ${formatCurrency((basePrice * MAX_PRICE_OVERRIDE_RATIO) / 100)})`}
              name={`override-${item.skuId}`}
              inputMode="numeric"
              value={formatKopecksForInput(item.unitPriceOverrideAmount)}
              onChange={(e) => {
                const next = parseRublesToKopecks(e.target.value);
                if (next == null) return;
                onChange({ unitPriceOverrideAmount: next });
              }}
              error={
                overrideCheck.ok
                  ? null
                  : overrideCheck.reason === 'above_max_ratio'
                    ? `Допустимо 0 — ${formatCurrency(overrideCheck.max / 100)}`
                    : 'Введите целое число ≥ 0'
              }
            />
            <TextField
              label="Причина"
              name={`reason-${item.skuId}`}
              value={item.overrideReason ?? ''}
              onChange={(e) => onChange({ overrideReason: e.target.value })}
              error={reasonMissing}
            />
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-dashed border-current pt-2 text-sm">
        <span className="text-app-muted">
          Итого по позиции: {formatCurrency(lineTotal / 100)}
        </span>
        {serverError && (
          <span className="text-app-danger text-xs" role="alert">
            {serverError}
          </span>
        )}
      </div>
    </div>
  );
}
