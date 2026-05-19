'use client';

import { Provider } from 'react-redux';
import { useState } from 'react';

import { makeStore } from '@/app/providers/store/configure';
// Sprint 3b: side effect — features/add-to-cart registers QuickAddSheet
// and SplitPaymentSheet into entities/product's slot store. Must run on
// the client because `registerSheetSlot` is `'use client'`-bound (it
// reads from a `useSyncExternalStore`-backed slot map). Importing this
// from the server `app/layout.tsx` triggered a "registerSheetSlot()
// called from the server" RSC violation; we anchor it to the nearest
// client provider instead.
import '@/features/add-to-cart';

export default function StoreProvider({ children }) {
  const [store] = useState(() => makeStore());
  return <Provider store={store}>{children}</Provider>;
}
