'use client';

import { useCallback, useEffect, useReducer } from 'react';

import { generateIdempotencyKey } from '@/entities/order';

// Walk-in order form state. Lives entirely in the client — there's no
// draft persistence (out of scope for MVP per SPEC), so a page reload
// drops everything.
//
// Items carry the SKU metadata snapshot picked from SkuPickerModal so the
// item row can render base price / supplier badge / currency without
// re-fetching. The submit payload only forwards what the backend cares
// about (skuId, quantity, optional override + reason).

const EMPTY_PROFILE = {
  fullName: '',
  phone: '',
  email: '',
};

const EMPTY_RECIPIENT = {
  fullNameRu: '',
  fullNameLat: '',
  phone: '',
  email: '',
  passportSerial: '',
  passportNumber: '',
  passportIssueDate: '',
  birthDate: '',
  inn: '',
};

const EMPTY_PAYMENT = {
  method: 'cash',
  reference: '',
  // datetime-local input value; "" means "send now" — useSubmitWalkInOrder
  // will fill the timestamp at submit time so a long-open form doesn't ship
  // a stale paidAt.
  paidAt: '',
};

function buildInitialState() {
  return {
    profile: { ...EMPTY_PROFILE },
    recipient: { ...EMPTY_RECIPIENT },
    items: [],
    pickupCarrier: '',
    pickupPointId: '',
    pickupPointLabel: '',
    deliveryAmount: 0,
    payment: { ...EMPTY_PAYMENT },
    // Generated lazily by the hook (crypto.randomUUID inside the reducer
    // closure trips React strict-mode double-invoke). The hook seeds this
    // field at mount via SEED_IDEMPOTENCY_KEY.
    idempotencyKey: '',
  };
}

const ACTIONS = {
  SEED_IDEMPOTENCY_KEY: 'SEED_IDEMPOTENCY_KEY',
  SET_PROFILE_FIELD: 'SET_PROFILE_FIELD',
  SET_RECIPIENT_FIELD: 'SET_RECIPIENT_FIELD',
  ADD_ITEM: 'ADD_ITEM',
  REMOVE_ITEM: 'REMOVE_ITEM',
  UPDATE_ITEM: 'UPDATE_ITEM',
  SET_PICKUP: 'SET_PICKUP',
  SET_DELIVERY_AMOUNT: 'SET_DELIVERY_AMOUNT',
  SET_PAYMENT_FIELD: 'SET_PAYMENT_FIELD',
  RESET_FORM: 'RESET_FORM',
};

function reducer(state, action) {
  switch (action.type) {
    case ACTIONS.SEED_IDEMPOTENCY_KEY:
      // Idempotent: once seeded, don't overwrite — the same key must
      // survive across retries so the backend's 24h dedup cache returns
      // the original 201 instead of double-creating.
      if (state.idempotencyKey) return state;
      return { ...state, idempotencyKey: action.key };

    case ACTIONS.SET_PROFILE_FIELD:
      return {
        ...state,
        profile: { ...state.profile, [action.field]: action.value },
      };

    case ACTIONS.SET_RECIPIENT_FIELD:
      return {
        ...state,
        recipient: { ...state.recipient, [action.field]: action.value },
      };

    case ACTIONS.ADD_ITEM: {
      // De-duplicate by skuId: re-adding the same SKU bumps qty by 1
      // instead of creating a second row (admin's typical instinct when
      // a customer asks for two pairs of the same shoe).
      const existing = state.items.findIndex(
        (it) => it.skuId === action.item.skuId,
      );
      if (existing !== -1) {
        const next = [...state.items];
        const it = next[existing];
        next[existing] = {
          ...it,
          quantity: Math.min(99, (it.quantity ?? 1) + 1),
        };
        return { ...state, items: next };
      }
      return {
        ...state,
        items: [
          ...state.items,
          {
            skuId: action.item.skuId,
            quantity: 1,
            // null override = use catalog price (the default). When the
            // admin enables the inline price-override toggle the field is
            // set to an integer; null means "no override row submitted".
            unitPriceOverrideAmount: null,
            overrideReason: '',
            // Snapshot from SkuPickerModal — display only, not part of the
            // submit payload.
            sku: action.item,
          },
        ],
      };
    }

    case ACTIONS.REMOVE_ITEM:
      return {
        ...state,
        items: state.items.filter((it) => it.skuId !== action.skuId),
      };

    case ACTIONS.UPDATE_ITEM:
      return {
        ...state,
        items: state.items.map((it) =>
          it.skuId === action.skuId ? { ...it, ...action.patch } : it,
        ),
      };

    case ACTIONS.SET_PICKUP:
      return {
        ...state,
        pickupCarrier: action.carrier,
        pickupPointId: action.pointId,
        pickupPointLabel: action.label ?? '',
      };

    case ACTIONS.SET_DELIVERY_AMOUNT:
      return { ...state, deliveryAmount: action.value };

    case ACTIONS.SET_PAYMENT_FIELD:
      return {
        ...state,
        payment: { ...state.payment, [action.field]: action.value },
      };

    case ACTIONS.RESET_FORM:
      // Regenerate the idempotency key — the next submit is a new order.
      return {
        ...buildInitialState(),
        idempotencyKey: generateIdempotencyKey(),
      };

    default:
      return state;
  }
}

export function useWalkInOrderForm() {
  const [state, dispatch] = useReducer(reducer, undefined, buildInitialState);

  // Seed the idempotency key exactly once on first mount. The reducer's
  // SEED_IDEMPOTENCY_KEY branch is no-op if the key is already set, so
  // strict-mode's intentional double-effect-invoke is safe — the second
  // dispatch hits the early-return.
  useEffect(() => {
    dispatch({
      type: ACTIONS.SEED_IDEMPOTENCY_KEY,
      key: generateIdempotencyKey(),
    });
  }, []);

  const setProfileField = useCallback((field, value) => {
    dispatch({ type: ACTIONS.SET_PROFILE_FIELD, field, value });
  }, []);

  const setRecipientField = useCallback((field, value) => {
    dispatch({ type: ACTIONS.SET_RECIPIENT_FIELD, field, value });
  }, []);

  const addItem = useCallback((item) => {
    dispatch({ type: ACTIONS.ADD_ITEM, item });
  }, []);

  const removeItem = useCallback((skuId) => {
    dispatch({ type: ACTIONS.REMOVE_ITEM, skuId });
  }, []);

  const updateItem = useCallback((skuId, patch) => {
    dispatch({ type: ACTIONS.UPDATE_ITEM, skuId, patch });
  }, []);

  const setPickup = useCallback((carrier, pointId, label) => {
    dispatch({ type: ACTIONS.SET_PICKUP, carrier, pointId, label });
  }, []);

  const setDeliveryAmount = useCallback((value) => {
    dispatch({ type: ACTIONS.SET_DELIVERY_AMOUNT, value });
  }, []);

  const setPaymentField = useCallback((field, value) => {
    dispatch({ type: ACTIONS.SET_PAYMENT_FIELD, field, value });
  }, []);

  const resetForm = useCallback(() => {
    dispatch({ type: ACTIONS.RESET_FORM });
  }, []);

  return {
    state,
    setProfileField,
    setRecipientField,
    addItem,
    removeItem,
    updateItem,
    setPickup,
    setDeliveryAmount,
    setPaymentField,
    resetForm,
  };
}
