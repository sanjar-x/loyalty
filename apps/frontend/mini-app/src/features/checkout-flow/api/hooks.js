/** Sprint 3d: Checkout-flow RTKQ hooks + rate quote + cart merge. */
import { enhancedApi, customApi } from '@/app/providers/store/instance';
import {
  setPendingIdempotencyKey,
  clearPendingIdempotencyKey,
} from '@/shared/api/base-api/baseApi';

export const INITIATE_CHECKOUT_URL = '/api/v1/cart/checkout';

export { clearPendingIdempotencyKey };

export const useInitiateCheckoutMutation = () => {
  const [trigger, state] = enhancedApi.useInitiateCheckoutApiV1CartCheckoutPostMutation();
  const wrapped = (body) => {
    // CHK-006: Idempotency-Key via side-channel in the baseQuery registry.
    if (body?.__idempotencyKey) {
      setPendingIdempotencyKey(INITIATE_CHECKOUT_URL, body.__idempotencyKey);
    }
    return trigger({
      initiateCheckoutRequest: {
        pickupPointId: body?.pickupPointId,
        pickupCarrier: body?.pickupCarrier,
        recipientId: body?.recipientId,
      },
    });
  };
  return [wrapped, state];
};

export const useConfirmCheckoutMutation = () => {
  const [trigger, state] = enhancedApi.useConfirmCheckoutApiV1CartCheckoutConfirmPostMutation();
  const wrapped = (body) => trigger({ confirmCheckoutRequest: { attemptId: body?.attemptId } });
  return [wrapped, state];
};

export const useCancelCheckoutMutation =
  enhancedApi.useCancelCheckoutApiV1CartCheckoutCancelPostMutation;

export const useGetAnonymousCartTokenMutation =
  enhancedApi.useCreateAnonymousTokenApiV1CartAnonymousTokenPostMutation;

export const useMergeCartMutation = () => {
  const [trigger, state] = enhancedApi.useMergeCartsApiV1CartMergePostMutation();
  const wrapped = ({ anonymousToken }) => trigger({ mergeCartRequest: { anonymousToken } });
  return [wrapped, state];
};

/* Rate quote — custom hook (admin-only path under the hood) */
export const useGetRateQuoteMutation = customApi.useGetRateQuoteMutation;
