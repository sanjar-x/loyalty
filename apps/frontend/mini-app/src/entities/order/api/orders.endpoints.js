/**
 * RTKQ endpoint enhancement config'lari — Orders / Recipients / Payments.
 */
export const orderEndpoints = {
  /* ─── Orders ─── */
  listMyOrdersApiV1OrdersGet: {
    providesTags: (result) => {
      const items = Array.isArray(result?.items) ? result.items : [];
      if (!items.length) return ['Orders'];
      return [
        'Orders',
        ...items
          .map((o) => o?.orderId)
          .filter(Boolean)
          .map((id) => ({ type: 'Orders', id })),
      ];
    },
  },
  getOrderApiV1OrdersOrderIdGet: {
    providesTags: (_r, _e, arg) => [{ type: 'Orders', id: arg?.orderId }],
  },
  getOrderTrackingApiV1OrdersOrderIdTrackingGet: {
    providesTags: (_r, _e, arg) => [{ type: 'Orders', id: `tracking-${arg?.orderId}` }],
    keepUnusedDataFor: 60,
  },
  cancelOrderApiV1OrdersOrderIdCancelPost: {
    invalidatesTags: (_r, _e, arg) => [{ type: 'Orders', id: arg?.orderId }, 'Orders'],
  },
  refreshRecipientApiV1OrdersOrderIdRefreshRecipientPost: {
    invalidatesTags: (_r, _e, arg) => [{ type: 'Orders', id: arg?.orderId }],
  },
  changePickupPointApiV1OrdersOrderIdPickupPointPatch: {
    invalidatesTags: (_r, _e, arg) => [{ type: 'Orders', id: arg?.orderId }],
  },

  /* ─── Recipients ─── */
  listMyRecipientsApiV1RecipientsGet: {
    providesTags: (result) => {
      const items = Array.isArray(result?.items) ? result.items : [];
      if (!items.length) return ['Recipients'];
      return [
        'Recipients',
        ...items
          .map((r) => r?.recipientId)
          .filter(Boolean)
          .map((id) => ({ type: 'Recipients', id })),
      ];
    },
  },
  getRecipientApiV1RecipientsRecipientIdGet: {
    providesTags: (_r, _e, arg) => [{ type: 'Recipients', id: arg?.recipientId }],
  },
  createRecipientApiV1RecipientsPost: { invalidatesTags: ['Recipients'] },
  updateRecipientApiV1RecipientsRecipientIdPatch: {
    invalidatesTags: (_r, _e, arg) => [{ type: 'Recipients', id: arg?.recipientId }, 'Recipients'],
  },
  archiveRecipientApiV1RecipientsRecipientIdDelete: {
    invalidatesTags: ['Recipients'],
  },

  /* ─── Payments ─── */
  getPaymentIntentApiV1PaymentsIntentsIntentIdGet: {
    providesTags: (_r, _e, arg) => [{ type: 'Payments', id: arg?.intentId }],
    keepUnusedDataFor: 30,
  },
};
