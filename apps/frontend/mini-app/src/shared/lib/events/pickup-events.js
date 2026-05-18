/**
 * Pickup selection event bus — pickup-selection (URL params) announces,
 * the checkout-flow store listens and updates its state.
 *
 * Sprint 3e: breaks the cross-feature dependency pickup-selection → checkout-flow.
 * pickup-selection does not know about the checkout FSM; checkout subscribes
 * to the event and decides itself how to react (via setPickup).
 */

const pickupTarget = typeof EventTarget !== 'undefined' ? new EventTarget() : null;
const PICKUP_SELECTED_EVENT = 'pickup:selected';

export function emitPickupSelected(pickup) {
  pickupTarget?.dispatchEvent(new CustomEvent(PICKUP_SELECTED_EVENT, { detail: pickup }));
}

export function onPickupSelected(listener) {
  if (!pickupTarget) return () => {};
  const handler = (e) => listener(e.detail);
  pickupTarget.addEventListener(PICKUP_SELECTED_EVENT, handler);
  return () => pickupTarget.removeEventListener(PICKUP_SELECTED_EVENT, handler);
}
