"use client";

import { use } from "react";

import CategoryPageClient from "./CategoryPageClient";

function safeDecodeSegment(s) {
  try {
    return decodeURIComponent(String(s ?? ""));
  } catch {
    return String(s ?? "");
  }
}

export default function CategoryPage({ params }) {
  const { path } = use(params);
  const segments = Array.isArray(path) ? path.map(safeDecodeSegment) : [];
  return <CategoryPageClient segments={segments} />;
}
