/**
 * Passport RTKQ hook re-exports.
 *
 * Backed by ADR-011 (Passport as Independent Bounded Context, accepted
 * 2026-05-19). Five customer endpoints live under `/api/v1/passports/*`:
 *   POST           — create
 *   GET            — list (own, non-archived)
 *   GET    /{id}   — read one
 *   PATCH  /{id}   — partial update
 *   DELETE /{id}   — soft-delete (is_archived=true)
 *
 * Hooks are thin re-exports of the codegen names — the long codegen
 * identifiers stay inside the entity, consumers get short aliases.
 * `cart`-style optimistic patches aren't introduced here yet — the
 * Passport flow has no high-frequency mutations on the buy-now path.
 */
import {
  useArchivePassportApiV1PassportsPassportIdDeleteMutation,
  useCreatePassportApiV1PassportsPostMutation,
  useGetPassportApiV1PassportsPassportIdGetQuery,
  useListMyPassportsApiV1PassportsGetQuery,
  useUpdatePassportApiV1PassportsPassportIdPatchMutation,
} from '@/shared/api/codegen/api';

export function useListMyPassportsQuery(arg, opts) {
  return useListMyPassportsApiV1PassportsGetQuery(arg ?? undefined, opts);
}

export function useGetPassportQuery(passportId, opts) {
  return useGetPassportApiV1PassportsPassportIdGetQuery(
    { passportId },
    { skip: !passportId, ...(opts || {}) }
  );
}

export function useCreatePassportMutation() {
  const [trigger, state] = useCreatePassportApiV1PassportsPostMutation();
  const wrapped = (body) => trigger({ createPassportRequest: body });
  return [wrapped, state];
}

export function useUpdatePassportMutation() {
  const [trigger, state] = useUpdatePassportApiV1PassportsPassportIdPatchMutation();
  const wrapped = ({ passportId, ...body }) => trigger({ passportId, updatePassportRequest: body });
  return [wrapped, state];
}

export const useArchivePassportMutation = useArchivePassportApiV1PassportsPassportIdDeleteMutation;
