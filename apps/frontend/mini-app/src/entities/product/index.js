// Public API. Do not reach into the slice from outside — only through this file.
export { default as ProductCard } from './ui/ProductCard';
export { default as ProductPrice } from './ui/ProductPrice';
export { default as ProductImageCarousel } from './ui/ProductImageCarousel';
export { default as ProductImageGallery } from './ui/ProductImageGallery';
export { default as ProductInfo } from './ui/ProductInfo';
export { default as ProductSection } from './ui/ProductSection';
export { default as ProductShippingOptions } from './ui/ProductShippingOptions';
export { default as ProductSizes } from './ui/ProductSizes';
export { default as ProductSkuSelector } from './ui/ProductSkuSelector';

export * from './lib/mapProductCard';
export * from './lib/mapStorefrontProduct';
export * from './lib/productImageHints';
export * from './lib/attributes';
export * from './lib/photoUrl';

// RTK Query endpoint config — re-exported so the store builder can collect
// all entity APIs into a single enhanceEndpoints call (see shared/api/base-api).
export { productEndpoints } from './api/products.endpoints';
export * from './lib/transformers';
export * from './api/hooks';
