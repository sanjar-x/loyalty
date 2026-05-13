import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

function ProductContent({ id }: { id: string }) {
  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold">Product #{id}</h1>
      <p className="text-muted-foreground text-sm">
        Product detail page placeholder
      </p>
    </div>
  );
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
      <ProductContent id={id} />
    </Suspense>
  );
}
