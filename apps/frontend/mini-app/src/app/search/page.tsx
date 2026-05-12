"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function SearchRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const query = searchParams.get("query") ?? "";
    const categoryId = searchParams.get("category_id") ?? "";
    const typeId = searchParams.get("type_id") ?? "";

    const params = new URLSearchParams();
    if (query) params.set("query", query);
    if (categoryId) params.set("category_id", categoryId);
    if (typeId) params.set("type_id", typeId);

    router.replace(`/?${params.toString()}`);
  }, [router, searchParams]);

  return null;
}

export default function SearchPage() {
  return (
    <Suspense>
      <SearchRedirect />
    </Suspense>
  );
}
