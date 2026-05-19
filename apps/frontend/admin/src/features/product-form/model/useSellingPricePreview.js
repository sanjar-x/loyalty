'use client';

import { useSuppliers } from '@/entities/supplier';

import { useContextForSupplierType } from './useContextForSupplierType';
import { useSkuPricingPreview } from './useSkuPricingPreview';

const RUB_FORMATTER = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

function formatPreviewPrice(finalPrice, currency = 'RUB') {
  const num = Number(finalPrice);
  if (!Number.isFinite(num)) return String(finalPrice);
  const formatted = RUB_FORMATTER.format(num);
  return currency === 'RUB' ? `${formatted} ₽` : `${currency} ${formatted}`;
}

/**
 * Humanise a snake_case code into a Russian-ish label as a last-resort
 * fallback. Used when the backend ships the legacy v1 `components` dict
 * (no breakdown). Once every formula version has migrated to AST v2 we
 * can drop this — but the dict will linger as a deprecated alias for a
 * release or two.
 */
function humanise(code) {
  return code
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part, idx) =>
      idx === 0 ? part.charAt(0).toUpperCase() + part.slice(1) : part,
    )
    .join(' ');
}

/**
 * Backend snapshot 2026-05-12 (PR #79 — supersedes the reverted PR #78
 * `componentsBreakdown`) adds `bindings: FormulaBindingValue[]`, an
 * ordered list of `{name, componentTag, label, isVisible, value}` rows.
 * We prefer it when present; otherwise we synthesise the same internal
 * row shape from the legacy `components` dict so the UI stays
 * single-pathed.
 *
 * Internal row shape consumed by `<ProductDetailsForm>`:
 *   { code, name, value, displayValue, isFinal }
 *
 * Mapping from `FormulaBindingValue` → internal row:
 *   code         ← binding.name                       // stable machine id, React key
 *   name         ← binding.label || humanise(name)    // displayed label, label may be null for legacy formulas
 *   value        ← binding.value ?? ''
 *   isFinal      ← binding.componentTag === 'final_price'
 */
export function deriveBreakdown(preview) {
  const currency = preview?.currency ?? 'RUB';
  if (Array.isArray(preview?.bindings)) {
    return preview.bindings
      .filter((row) => row && row.isVisible !== false)
      .map((row) => {
        const rawValue = row.value ?? '';
        return {
          code: row.name,
          name: row.label || humanise(row.name),
          value: String(rawValue),
          displayValue: formatPreviewPrice(rawValue, currency),
          isFinal: row.componentTag === 'final_price',
        };
      });
  }
  if (preview?.components && typeof preview.components === 'object') {
    const finalValue =
      preview.finalPrice != null ? String(preview.finalPrice) : null;
    return Object.entries(preview.components).map(([code, value]) => ({
      code,
      name: humanise(code),
      value: String(value),
      displayValue: formatPreviewPrice(value, currency),
      // Legacy dict has no componentTag marker — best-effort: match the
      // row whose value equals finalPrice, otherwise none.
      isFinal: finalValue != null && String(value) === finalValue,
    }));
  }
  return [];
}

/**
 * Adapter around `useSkuPricingPreview` that resolves the supplier
 * context, then returns the result in a shape ready to drop into a
 * disabled <MoneyInput>.
 *
 * Pre-fix the formula result lived in a separate green card below the
 * price row, and the merchandiser was given an editable «Цена продажи»
 * input on top of that. Editing was never the intent — selling price
 * is fully derived from `purchasePrice` via the ADR-005 formula. The
 * input is now read-only and displays the calculated value directly.
 *
 * Returns:
 *   - `value`: `{amount, currency} | null` — money-shape value to feed
 *     a disabled MoneyInput. Null while loading / no purchase price /
 *     missing supplier — caller decides whether to show empty or fall
 *     back to a stored manual price.
 *   - `helperText`: string | null — doubles as the loading indicator
 *     («Считаем цену продажи…»), the formula version tag («Формула v3»),
 *     and any soft failure copy. Caller should NOT route this into
 *     MoneyInput's `errorText` slot — preview hiccups must not paint
 *     the field red.
 *   - `breakdown`: ordered list of `{code, name, value, isFinal}` rows
 *     from the AST v2 `componentsBreakdown` payload (with the legacy
 *     `components` dict synthesised into the same shape when present).
 *     The caller renders this under an expander; the row with
 *     `isFinal === true` should read as the headline value.
 */
export function useSellingPricePreview({
  productId = null,
  categoryId,
  supplierId,
  purchasePrice,
}) {
  const { data: suppliersData, error: suppliersError } = useSuppliers();
  const supplier = (suppliersData?.items ?? []).find(
    (s) => s.id === supplierId,
  );
  const supplierType = supplier?.type ?? null;
  const { data: contextId, error: contextError } =
    useContextForSupplierType(supplierType);

  const { preview, loading, error } = useSkuPricingPreview({
    productId,
    categoryId,
    contextId,
    purchasePrice,
    supplierId,
    enabled: Boolean(categoryId && contextId),
  });

  if (!purchasePrice?.amount || Number(purchasePrice.amount) <= 0) {
    return { value: null, helperText: null, breakdown: [] };
  }
  if (!supplierId) {
    return {
      value: null,
      helperText: 'Выберите поставщика для расчёта цены продажи',
      breakdown: [],
    };
  }
  if (suppliersError) {
    return {
      value: null,
      helperText: '⚠ Не удалось загрузить поставщиков',
      breakdown: [],
    };
  }
  if (contextError) {
    return {
      value: null,
      helperText: `⚠ ${contextError.message}`,
      breakdown: [],
    };
  }
  if (suppliersData && !supplier) {
    return {
      value: null,
      helperText: '⚠ Поставщик не найден в активном списке',
      breakdown: [],
    };
  }
  // Both queries still resolving — stay silent rather than flash a value.
  if (!supplierType || !contextId) {
    return { value: null, helperText: null, breakdown: [] };
  }
  if (loading) {
    return { value: null, helperText: 'Считаем цену продажи…', breakdown: [] };
  }
  if (error) {
    return {
      value: null,
      helperText: `⚠ Не удалось рассчитать: ${error}`,
      breakdown: [],
    };
  }
  if (!preview || preview.finalPrice == null) {
    return { value: null, helperText: null, breakdown: [] };
  }
  const currency = preview.currency ?? 'RUB';
  const amount = Number(preview.finalPrice);
  const value = Number.isFinite(amount)
    ? { amount: Math.round(amount), currency }
    : null;
  const helperText =
    preview.formulaVersionNumber != null
      ? `Формула v${preview.formulaVersionNumber}`
      : null;
  const breakdown = deriveBreakdown(preview);
  return { value, helperText, breakdown };
}
