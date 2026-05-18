/** Sprint 3d: Order RTKQ hooks. */
import { enhancedApi } from '@/app/providers/store/instance';
import { setPendingIdempotencyKey } from '@/shared/api/base-api/baseApi';

export const CREATE_ORDER_URL = '/api/v1/orders';

export const useListOrdersQuery = (arg, opts) =>
  enhancedApi.useListMyOrdersApiV1OrdersGetQuery({ limit: arg?.limit, cursor: arg?.cursor }, opts);

export const useGetOrderByIdQuery = (orderId, opts) =>
  enhancedApi.useGetOrderApiV1OrdersOrderIdGetQuery({ orderId }, opts);

export const useGetOrderTrackingQuery = (orderId, opts) =>
  enhancedApi.useGetOrderTrackingApiV1OrdersOrderIdTrackingGetQuery({ orderId }, opts);

export const useCreateOrderMutation = () => {
  const [trigger, state] = enhancedApi.useCreateOrderApiV1OrdersPostMutation();
  const wrapped = (body) => {
    if (body?.__idempotencyKey) {
      setPendingIdempotencyKey(CREATE_ORDER_URL, body.__idempotencyKey);
    }
    return trigger({
      createOrderRequest: {
        cartId: body?.cartId,
        snapshotId: body?.snapshotId,
        idempotencyKey: body?.idempotencyKey,
        paymentProvider: body?.paymentProvider || 'fake',
        deliveryQuoteId: body?.deliveryQuoteId ?? null,
      },
    });
  };
  return [wrapped, state];
};

export const useCancelOrderMutation = () => {
  const [trigger, state] = enhancedApi.useCancelOrderApiV1OrdersOrderIdCancelPostMutation();
  const wrapped = ({ orderId, reason }) =>
    trigger({
      orderId,
      cancelOrderRequest: reason ? { reason } : {},
    });
  return [wrapped, state];
};

const adminOnlyMutation = () => [
  () => Promise.reject(new Error('Admin operation — not exposed in customer app')),
  { isLoading: false, isError: false, error: undefined, reset: () => {} },
];

const pendingFeatureQuery = () => ({
  data: undefined,
  isLoading: false,
  isFetching: false,
  isError: false,
  error: undefined,
  refetch: () => Promise.resolve(),
});

export const useUpdateOrderStatusMutation = adminOnlyMutation;
export const useGetOrderStatusQuery = () => ({ ...pendingFeatureQuery(), data: null });
