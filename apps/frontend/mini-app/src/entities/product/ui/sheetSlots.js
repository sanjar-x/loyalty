/**
 * Sprint 3b: DI slot pattern to break the entity → feature dependency.
 *
 * ProductCard and ProductPrice (entity) render sheets implemented by the
 * `add-to-cart` feature. Importing `@/features/add-to-cart` directly from
 * an entity violates FSD (an entity must not know about a feature).
 *
 * Solution: the entity declares a slot for the sheet; the feature registers
 * its component during init. Analogous to the authStatus DI seam in
 * shared/api/base-api.
 */

'use client';

import { createElement, useSyncExternalStore } from 'react';

const slots = {
  QuickAddSheet: null,
  SplitPaymentSheet: null,
};

const listeners = new Set();

function notify() {
  for (const l of listeners) l();
}

export function registerSheetSlot(name, Component) {
  if (!(name in slots)) return;
  slots[name] = Component;
  notify();
}

function subscribe(cb) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function useSlot(name) {
  return useSyncExternalStore(
    subscribe,
    () => slots[name],
    () => null
  );
}

// Sprint 3b: createElement instead of JSX to avoid the
// react-hooks/static-components warning (the component comes from an
// external store, not created on every render).
export function QuickAddSheetSlot(props) {
  const Component = useSlot('QuickAddSheet');
  if (!Component) return null;
  return createElement(Component, props);
}

export function SplitPaymentSheetSlot(props) {
  const Component = useSlot('SplitPaymentSheet');
  if (!Component) return null;
  return createElement(Component, props);
}
