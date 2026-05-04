"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AddToHomePage() {
  const router = useRouter();

  useEffect(() => {
    window.location.href =
      "https://t.me/loyaltymarketbot/?startapp&addToHomeScreen";
  }, []);

  return null;
}
