export { default as PromocodeCard } from './ui/PromocodeCard';
export { default as CreatePromocodeModal } from './ui/CreatePromocodeModal';

// TODO: replace mock-backed API with real backend integration when /api/promocodes is ready.
export {
  getPromocodes,
  createPromocode,
  deletePromocode,
} from './api/promocodes.mock';
