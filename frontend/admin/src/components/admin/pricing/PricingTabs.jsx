'use client';

import { cn } from '@/lib/utils';
import { usePricingPage } from './PricingPageProvider';

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
      <div className="flex gap-0 border-b border-app-border">
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
              <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-app-text" />
            )}
          </button>
        ))}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
