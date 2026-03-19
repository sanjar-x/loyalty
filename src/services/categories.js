import { productCategoryTree, findProductCategoryPath } from '@/data/productCategories';

export function getProductCategories() {
  return [...productCategoryTree];
}

export { findProductCategoryPath };
