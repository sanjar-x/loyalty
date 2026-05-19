// Public API of the passport-form feature slice (ADR-011).
// Consumers (features/buy-now-checkout PassportStep, future cart-flow
// checkout passport sheet) MUST import from here — deep paths are
// blocked by ESLint (FSD `no-restricted-imports`).

export { default as PassportForm } from './ui/PassportForm';
export { default as PassportPicker } from './ui/PassportPicker';
export { usePassportForm } from './model/usePassportForm';
export { validatePassport } from './lib/validators';
export {
  maskRuDateInput,
  normaliseFullName,
  normaliseInn,
  normalisePassportNumber,
  normalisePassportSerial,
  ruDateToIso,
} from './lib/normalizers';
