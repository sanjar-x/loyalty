'use client';

import { cn } from '@/shared/lib/utils';
import { usePricingPage } from '@/features/pricing/model/PricingPageProvider';

const TABS = [
  { key: 'formula', label: 'Формула' },
  { key: 'variables', label: 'Переменные' },
  { key: 'categories', label: 'Категории' },
  { key: 'settings', label: 'Настройки' },
];

export function PricingTabs({ children }) {
  const { activeTab, setActiveTab } = usePricingPage();

  return (
    <div>
      <div className="border-app-border flex gap-0 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'relative px-4 py-2.5 text-sm font-medium transition-colors',
              activeTab === tab.key
                ? 'text-app-text'
                : 'text-app-muted hover:text-app-text',
            )}
          >
            {tab.label}
            {activeTab === tab.key && (
              <span className="bg-app-text absolute inset-x-0 bottom-0 h-0.5 rounded-full" />
            )}
          </button>
        ))}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
