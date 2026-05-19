import { genId } from '@/shared/lib/genId';
import { promocodesSeed } from '@/shared/mocks/promocodes';

let promocodes = [...promocodesSeed];

export function getPromocodes() {
  return [...promocodes];
}

export async function createPromocode(data) {
  const promo = { id: genId('promo'), ...data };
  promocodes = [promo, ...promocodes];
  return promo;
}

export async function deletePromocode(id) {
  promocodes = promocodes.filter((p) => p.id !== id);
}
