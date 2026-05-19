export { PromocodeCard } from './ui/PromocodeCard';
export { CreatePromocodeModal } from './ui/CreatePromocodeModal';

// TODO: replace mock-backed API with real backend integration when /api/promocodes is ready.
export {
  getPromocodes,
  createPromocode,
  deletePromocode,
} from './api/promocodes.mock';
