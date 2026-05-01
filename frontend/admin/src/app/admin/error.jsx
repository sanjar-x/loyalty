'use client';

export default function AdminError({ error, reset }) {
  const isDev = process.env.NODE_ENV === 'development';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        padding: '40px 20px',
        textAlign: 'center',
      }}
    >
      <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Произошла ошибка</h2>
      {isDev && error?.message ? (
        <p style={{ color: '#7e7e7e', fontSize: '14px', maxWidth: '480px' }}>
          {error.message}
        </p>
      ) : (
        <p style={{ color: '#7e7e7e', fontSize: '14px' }}>
          Что-то пошло не так. Попробуйте обновить страницу.
        </p>
      )}
      <button
        type="button"
        onClick={reset}
        style={{
          padding: '8px 24px',
          borderRadius: '8px',
          border: '1px solid #e0e0e0',
          background: '#fff',
          cursor: 'pointer',
          fontSize: '14px',
        }}
      >
        Попробовать снова
      </button>
    </div>
  );
}
