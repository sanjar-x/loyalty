import './globals.css';

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin panel for marketplace management',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
