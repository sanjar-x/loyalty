'use client';

import { Suspense } from 'react';
import { PricingPageProvider } from '@/features/pricing';

export default function PricingLayout({ children }) {
  return (
    <Suspense>
      <PricingPageProvider>{children}</PricingPageProvider>
    </Suspense>
  );
}
