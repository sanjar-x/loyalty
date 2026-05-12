import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

function CategoryContent({ category }: { category: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold capitalize">{category}</h1>
      <p className="text-muted-foreground text-sm">
        Category detail page placeholder
      </p>
    </div>
  );
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ category: string }>;
}) {
  const { category } = await params;
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
      <CategoryContent category={category} />
    </Suspense>
  );
}
