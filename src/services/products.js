import { productsSeed } from '@/data/products';

export function getProducts() {
  return [...productsSeed];
}
