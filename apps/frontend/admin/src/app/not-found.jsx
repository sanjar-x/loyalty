import Link from 'next/link';

// Root-level not-found boundary for URLs that fall outside the
// admin/login/invite trees — typos like /inviet/abc or /admnin would
// otherwise render Next.js's default unbranded 404 HTML. The admin
// shell has its own /admin/not-found.jsx for in-shell misses; this one
// covers the public surface.
export default function RootNotFound() {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily:
            'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
          background: '#f5f5f7',
          color: '#22252b',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '12px',
            padding: '40px 20px',
            textAlign: 'center',
          }}
        >
          <p style={{ fontSize: '14px', color: '#7e7e7e', margin: 0 }}>404</p>
          <h1 style={{ fontSize: '22px', fontWeight: 600, margin: 0 }}>
            Страница не найдена
          </h1>
          <p style={{ fontSize: '14px', color: '#7e7e7e', maxWidth: '420px' }}>
            Проверьте URL или вернитесь на главную.
          </p>
          <Link
            href="/admin"
            style={{
              marginTop: '8px',
              padding: '10px 22px',
              borderRadius: '12px',
              background: '#22252b',
              color: '#fff',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            На главную
          </Link>
        </div>
      </body>
    </html>
  );
}
