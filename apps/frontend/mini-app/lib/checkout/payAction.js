/**
 * Pay button pre-flight decision (CHK-005).
 *
 * Pay tugmasi har doim enabled — `disabled` prop ko'r-ko'rona UI'ni
 * yashirib qo'yadi va foydalanuvchi qaysi qadam yetishmayotganini
 * tushunmaydi. Endi handler `decideCheckoutAction(...)` orqali
 * keyingi xatti-harakatni tanlaydi va UI ko'rinadigan feedback beradi.
 *
 * Pure: hech qanday DOM, store yoki RTKQ'siz. UI shu yerda `action.type`
 * bo'yicha tarmoqlanadi (toast, scroll, sheet ochish, placeOrder).
 *
 * @typedef {{ type: "BUSY" }} ActionBusy
 * @typedef {{ type: "EMPTY_CART", message: string }} ActionEmptyCart
 * @typedef {{ type: "NEED_PICKUP", message: string }} ActionNeedPickup
 * @typedef {{ type: "NEED_QUOTE_REFRESH", message: string }} ActionNeedQuoteRefresh
 * @typedef {{ type: "NEED_RECIPIENT" | "NEED_CUSTOMS", message: string, field: string }} ActionNeedForm
 * @typedef {{ type: "READY" }} ActionReady
 * @typedef {ActionBusy|ActionEmptyCart|ActionNeedPickup|ActionNeedQuoteRefresh|ActionNeedForm|ActionReady} CheckoutAction
 */

export const CUSTOMS_FIELDS = Object.freeze([
  'passportSeries',
  'passportNumber',
  'issueDate',
  'birthDate',
  'inn',
]);

/**
 * @param {Object} params
 * @param {string} params.status                CheckoutStatus value
 * @param {string} params.initiatingStatus      CheckoutStatus.INITIATING constant
 * @param {string} params.confirmingStatus      CheckoutStatus.CONFIRMING constant
 * @param {number} params.selectedQuantity
 * @param {boolean} params.isPickupSelected
 * @param {boolean} params.isQuoteValid
 * @param {Object | null} params.recipient
 * @param {Object | null} params.customs
 * @param {(input: Object) => { ok: boolean, errors: Record<string, string> }} params.validate
 *   `validateRecipientForOrder` injected (test'da mock qilamiz).
 * @returns {CheckoutAction}
 */
export function decideCheckoutAction({
  status,
  initiatingStatus,
  confirmingStatus,
  selectedQuantity,
  isPickupSelected,
  isQuoteValid,
  recipient,
  customs,
  validate,
}) {
  if (status === initiatingStatus || status === confirmingStatus) {
    return { type: 'BUSY' };
  }
  if (!Number.isFinite(selectedQuantity) || selectedQuantity <= 0) {
    return { type: 'EMPTY_CART', message: 'Корзина пуста' };
  }
  if (!isPickupSelected) {
    return { type: 'NEED_PICKUP', message: 'Выберите пункт выдачи' };
  }
  if (!isQuoteValid) {
    return {
      type: 'NEED_QUOTE_REFRESH',
      message: 'Обновляем стоимость доставки…',
    };
  }
  const guard =
    typeof validate === 'function' ? validate({ recipient, customs }) : { ok: true, errors: {} };
  if (!guard.ok) {
    const firstField = Object.keys(guard.errors || {})[0] || '';
    const isCustomsField = CUSTOMS_FIELDS.includes(firstField);
    return {
      type: isCustomsField ? 'NEED_CUSTOMS' : 'NEED_RECIPIENT',
      message: isCustomsField ? 'Заполните паспортные данные и ИНН' : 'Заполните данные получателя',
      field: firstField,
    };
  }
  return { type: 'READY' };
}
