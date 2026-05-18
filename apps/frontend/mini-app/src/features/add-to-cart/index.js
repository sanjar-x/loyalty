/**
 * Sprint 3b: side-effect — register sheets in the entities/product slot
 * so that ProductCard/ProductPrice can render them without a cross-layer
 * import (entity → feature). DI seam pattern.
 */
import { registerSheetSlot } from '@/entities/product/ui/sheetSlots';

import QuickAddSheet from './ui/QuickAddSheet';
import SplitPaymentSheet from './ui/SplitPaymentSheet';

registerSheetSlot('QuickAddSheet', QuickAddSheet);
registerSheetSlot('SplitPaymentSheet', SplitPaymentSheet);

export { default as QuickAddSheet } from './ui/QuickAddSheet';
export { default as ProductAddToCart } from './ui/ProductAddToCart';
export { default as SplitPaymentSheet } from './ui/SplitPaymentSheet';
