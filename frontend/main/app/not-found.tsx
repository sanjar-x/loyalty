import Link from "next/link";

export default function NotFound() {
  return (
    <div className="lm-app-bg" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <h2 style={{ fontFamily: "Inter, sans-serif", fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          Страница не найдена
        </h2>
        <p style={{ fontFamily: "Inter, sans-serif", fontSize: "0.875rem", color: "#666", marginBottom: "1.5rem" }}>
          Такой страницы не существует
        </p>
        <Link
          href="/"
          style={{
            fontFamily: "Inter, sans-serif",
            fontSize: "0.875rem",
            fontWeight: 500,
            padding: "0.75rem 2rem",
            borderRadius: "9999px",
            border: "none",
            background: "#111",
            color: "#fff",
            textDecoration: "none",
            display: "inline-block",
          }}
        >
          На главную
        </Link>
      </div>
    </div>
  );
}
