import localFont from 'next/font/local';
import Script from 'next/script';

import { TelegramAppShell } from '@/app/_providers/telegram-app-shell';
import { Footer } from '@/components/layout/footer';
import { QueryProvider } from '@/components/providers/query-provider';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { ToastProvider } from '@/components/providers/toast-provider';

import type { Metadata, Viewport } from 'next';

import './globals.css';

const inter = localFont({
  src: [
    { path: '../../public/fonts/inter/inter-v20-cyrillic-regular.woff2', weight: '400' },
    { path: '../../public/fonts/inter/inter-v20-cyrillic-500.woff2', weight: '500' },
    { path: '../../public/fonts/inter/inter-v20-cyrillic-600.woff2', weight: '600' },
    { path: '../../public/fonts/inter/inter-v20-cyrillic-700.woff2', weight: '700' },
  ],
  variable: '--font-inter',
  display: 'swap',
});

const bebasNeue = localFont({
  src: '../../public/fonts/BebasNeueBold/BebasNeueBold.woff2',
  variable: '--font-bebas',
  weight: '700',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'LoyaltyMarket',
  description: 'Telegram Mini App Marketplace',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="ru"
      suppressHydrationWarning
      className={`${inter.variable} ${bebasNeue.variable} h-full antialiased`}
    >
      <head>
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      </head>
      <body
        className="flex min-h-full flex-col bg-white font-[family-name:var(--font-inter)] text-[#2D2D2D]"
        suppressHydrationWarning
      >
        <ThemeProvider>
          <QueryProvider>
            <TelegramAppShell>
              {children}
              <Footer />
            </TelegramAppShell>
            <ToastProvider />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
