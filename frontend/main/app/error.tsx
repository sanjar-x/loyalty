"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <div className="lm-app-bg" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <h2 style={{ fontFamily: "Inter, sans-serif", fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Что-то пошло не так
        </h2>
        <p style={{ fontFamily: "Inter, sans-serif", fontSize: "0.875rem", color: "#666", marginBottom: "1.5rem" }}>
          Попробуйте обновить страницу
        </p>
        <button
          onClick={reset}
          type="button"
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: "0.875rem",
            fontWeight: 500,
            padding: "0.75rem 2rem",
            borderRadius: "9999px",
            border: "none",
            background: "#111",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          Попробовать снова
        </button>
      </div>
    </div>
  );
}
