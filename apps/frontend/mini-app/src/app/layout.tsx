import './globals.css';
import localFont from 'next/font/local';
import Script from 'next/script';
import type { ReactNode } from 'react';
import type { Viewport } from 'next';

import WebViewErrorAlert from '@/widgets/WebViewErrorAlert';
import TelegramViewportManager from '@/widgets/TelegramViewportManager';
import InputFocusFix from '@/shared/lib/ios';
import InitTelegramMock from '@/shared/lib/dev';
import StoreProvider from '@/app/providers/StoreProvider';
import TelegramAppShell from '@/widgets/TelegramAppShell';
import Toaster from '@/shared/ui/Toaster';
// Sprint 3b: side-effect — registers QuickAddSheet/SplitPaymentSheet
// in the entities/product slot so ProductCard/ProductPrice can render them.
import '@/features/add-to-cart';

const inter = localFont({
  src: [
    {
      path: '../../public/fonts/inter/inter-v20-latin-regular.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-latin-500.woff2',
      weight: '500',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-latin-600.woff2',
      weight: '600',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-latin-700.woff2',
      weight: '700',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-cyrillic-regular.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-cyrillic-500.woff2',
      weight: '500',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-cyrillic-600.woff2',
      weight: '600',
      style: 'normal',
    },
    {
      path: '../../public/fonts/inter/inter-v20-cyrillic-700.woff2',
      weight: '700',
      style: 'normal',
    },
  ],
  variable: '--font-inter',
  display: 'swap',
});

const sfProRounded = localFont({
  src: '../../public/fonts/SFProRounded/SFProRounded-Medium.woff2',
  weight: '500',
  style: 'normal',
  variable: '--font-sf-rounded',
  display: 'swap',
});

const bebasNeue = localFont({
  src: '../../public/fonts/BebasNeueBold/BebasNeueBold.woff2',
  weight: '700',
  style: 'normal',
  variable: '--font-bebas',
  display: 'swap',
});

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="ru"
      className={`${inter.variable} ${bebasNeue.variable} ${sfProRounded.variable}`}
      suppressHydrationWarning
    >
      <head>
        <meta name="theme-color" content="#ffffff" />
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      </head>
      <body suppressHydrationWarning>
        <InitTelegramMock />
        <StoreProvider>
          <TelegramAppShell>
            <TelegramViewportManager />
            <InputFocusFix />
            {children}
            <Toaster />
            <WebViewErrorAlert />
          </TelegramAppShell>
        </StoreProvider>
      </body>
    </html>
  );
}
