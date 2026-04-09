"use client";

import { useEffect } from "react";

export default function InputFocusFix() {
  useEffect(() => {
    const onFocus = (e: FocusEvent) => {
      const t = e.target as HTMLElement | null;
      if (!t) return;

      if (t.tagName === "INPUT" || t.tagName === "TEXTAREA") {
        document.body.style.touchAction = "manipulation";
      }
    };

    document.addEventListener("focusin", onFocus);
    return () => document.removeEventListener("focusin", onFocus);
  }, []);

  return null;
}
