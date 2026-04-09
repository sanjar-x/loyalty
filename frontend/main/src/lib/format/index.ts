export { formatRub, formatRubCompact, formatSplitPayment } from "./price";
export { formatRuDateTime, formatUntilDate } from "./date";
export {
  buildProductPhotoUrl,
  buildBackendAssetUrl,
  getProductPhotoCandidates,
} from "./product-image";
export { buildBrandLogoUrl, getBrandLogoCandidates } from "./brand-image";
export { normalize, normalizeForCatalogSearch, getFirstLetter } from "./text";
export { pluralizeRu, pluralizeWithCount } from "./pluralize";
export { copyText } from "./clipboard";
export {
  asNonEmptyTrimmedString,
  asSafeImageSrc,
  isValidPhone,
  isValidEmail,
  isValidFullName,
} from "./validation";
