'use client';

import { useState } from 'react';

import { CategoryTabs } from './category-tabs';
import { FriendsSection } from './friends-section';
import { ProductGrid } from './product-grid';
import { SearchBar } from './search-bar';

export function HomePage() {
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-1 pb-4">
      <SearchBar />

      <CategoryTabs
        activeCategoryId={activeCategoryId}
        onCategoryChange={setActiveCategoryId}
      />

      <FriendsSection />

      <section className="mt-2">
        <h2 className="px-4 pb-2 text-base font-bold">Для вас</h2>
        <ProductGrid categoryId={activeCategoryId} />
      </section>
    </div>
  );
}
