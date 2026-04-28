'use client';

import { Suspense } from 'react';
import { PricingPageProvider } from '@/components/admin/pricing/PricingPageProvider';

export default function PricingLayout({ children }) {
  return (
    <Suspense>
      <PricingPageProvider>{children}</PricingPageProvider>
    </Suspense>
  );
}
