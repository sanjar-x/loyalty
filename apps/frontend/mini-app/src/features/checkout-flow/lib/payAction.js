/**
 * Pay button pre-flight decision (CHK-005, post-ADR-011).
 *
 * The Pay button is always enabled — a `disabled` prop blindly hides
 * the UI and the user can't tell which step is missing. The handler
 * picks the next action via `decideCheckoutAction(...)` and the UI
 * provides visible feedback (toast / scroll / open sheet / placeOrder).
 *
 * Pure: no DOM, no store, no RTKQ. The UI branches here based on
 * `action.type`.
 *
 * ADR-011: customs documents moved to the Passport bounded context.
 * For cross-border carts the customer must resolve a passport before
 * placing the order — the `NEED_PASSPORT` branch surfaces that gap so
 * the UI can open `<PassportSheet />` instead of toasting.
 *
 * @typedef {{ type: "BUSY" }} ActionBusy
 * @typedef {{ type: "EMPTY_CART", message: string }} ActionEmptyCart
 * @typedef {{ type: "NEED_PICKUP", message: string }} ActionNeedPickup
 * @typedef {{ type: "NEED_QUOTE_REFRESH", message: string }} ActionNeedQuoteRefresh
 * @typedef {{ type: "NEED_RECIPIENT", message: string, field: string }} ActionNeedRecipient
 * @typedef {{ type: "NEED_PASSPORT", message: string }} ActionNeedPassport
 * @typedef {{ type: "READY" }} ActionReady
 * @typedef {ActionBusy|ActionEmptyCart|ActionNeedPickup|ActionNeedQuoteRefresh|ActionNeedRecipient|ActionNeedPassport|ActionReady} CheckoutAction
 */

/**
 * @param {Object} params
 * @param {string} params.status                CheckoutStatus value
 * @param {string} params.initiatingStatus      CheckoutStatus.INITIATING constant
 * @param {string} params.confirmingStatus      CheckoutStatus.CONFIRMING constant
 * @param {number} params.selectedQuantity
 * @param {boolean} params.isPickupSelected
 * @param {boolean} params.isQuoteValid
 * @param {Object | null} params.recipient
 * @param {boolean} params.hasCrossBorderItems  true when any selected
 *                                              item is cross-border
 *                                              (use `selectHasCrossBorderItems`)
 * @param {string | null} params.passportId
 * @param {(input: { recipient: Object }) => { ok: boolean, errors: Record<string, string> }} params.validate
 *   `validateRecipientForOrder` injected (mocked in tests).
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
  hasCrossBorderItems,
  passportId,
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
  const guard = typeof validate === 'function' ? validate({ recipient }) : { ok: true, errors: {} };
  if (!guard.ok) {
    const firstField = Object.keys(guard.errors || {})[0] || '';
    return {
      type: 'NEED_RECIPIENT',
      message: 'Заполните данные получателя',
      field: firstField,
    };
  }
  // ADR-011 defence-in-depth: cross-border cart without a passport
  // would land on backend invariant I2 (422
  // PASSPORT_REQUIRED_FOR_CROSS_BORDER). Short-circuit here so the UI
  // can open PassportSheet before the round-trip.
  if (hasCrossBorderItems && !passportId) {
    return {
      type: 'NEED_PASSPORT',
      message: 'Для cross-border заказа нужен паспорт получателя',
    };
  }
  return { type: 'READY' };
}
