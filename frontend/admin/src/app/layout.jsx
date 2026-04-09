import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['cyrillic', 'latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata = {
  title: 'Admin Panel',
  description: 'Admin panel for marketplace management',
};

export default function RootLayout({ children }) {
  return (
    <html lang="ru" className={inter.variable} suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
