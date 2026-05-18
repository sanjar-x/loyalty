/** Sprint 3d: Recipient RTKQ hooks. */
import { enhancedApi } from '@/app/providers/store/instance';

export const useListMyRecipientsQuery = enhancedApi.useListMyRecipientsApiV1RecipientsGetQuery;

export const useGetRecipientQuery = (recipientId, opts) =>
  enhancedApi.useGetRecipientApiV1RecipientsRecipientIdGetQuery({ recipientId }, opts);

export const useCreateRecipientMutation = () => {
  const [trigger, state] = enhancedApi.useCreateRecipientApiV1RecipientsPostMutation();
  const wrapped = (body) => trigger({ createRecipientRequest: body });
  return [wrapped, state];
};

export const useUpdateRecipientMutation = () => {
  const [trigger, state] = enhancedApi.useUpdateRecipientApiV1RecipientsRecipientIdPatchMutation();
  const wrapped = ({ recipientId, ...body }) =>
    trigger({ recipientId, updateRecipientRequest: body });
  return [wrapped, state];
};

export const useArchiveRecipientMutation =
  enhancedApi.useArchiveRecipientApiV1RecipientsRecipientIdDeleteMutation;
