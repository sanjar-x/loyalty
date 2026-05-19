// Public API of the passport entity slice (ADR-011).
// Consumers (features/passport-form, features/buy-now-checkout, future
// cart-flow checkout) MUST import from here — deep paths are blocked by
// ESLint (FSD `no-restricted-imports`).

export {
  useArchivePassportMutation,
  useCreatePassportMutation,
  useGetPassportQuery,
  useListMyPassportsQuery,
  useUpdatePassportMutation,
} from './api/passportApi';

export { default as PassportCard } from './ui/PassportCard';
export { default as PassportBadge } from './ui/PassportBadge';

export { formatPassportIssueDate } from './lib/formatPassportIssueDate';
export { maskPassportNumber } from './lib/maskPassportNumber';

export { usePassportSelection } from './model/usePassportSelection';
