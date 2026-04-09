"use client";

import { Provider } from "react-redux";
import { useState, type ReactNode } from "react";
import { makeStore, type AppStore } from "@/lib/store/store";

export default function StoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState<AppStore>(() => makeStore());
  return <Provider store={store}>{children}</Provider>;
}
