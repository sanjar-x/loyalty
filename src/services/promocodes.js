import { promocodesSeed } from '@/data/promocodes';

let promocodes = [...promocodesSeed];

export function getPromocodes() {
  return [...promocodes];
}

export async function createPromocode(data) {
  const promo = { id: `promo-${Date.now()}`, ...data };
  promocodes = [promo, ...promocodes];
  return promo;
}

export async function deletePromocode(id) {
  promocodes = promocodes.filter((p) => p.id !== id);
}
