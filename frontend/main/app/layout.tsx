import "./globals.css";
import Script from "next/script";
import type { ReactNode } from "react";
import type { Viewport } from "next";

import { TelegramProvider } from "@/lib/telegram";
import TelegramAuthBootstrap from "@/components/blocks/telegram/TelegramAuthBootstrap";
import WebViewErrorAlert from "@/components/blocks/telegram/WebViewErrorAlert";
import InputFocusFix from "@/components/ios/InputFocusFix";
import StoreProvider from "@/components/providers/StoreProvider";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body suppressHydrationWarning>
        <StoreProvider>
          <TelegramProvider>
            <TelegramAuthBootstrap />
            <InputFocusFix />
            {children}
            <WebViewErrorAlert />
          </TelegramProvider>
        </StoreProvider>
      </body>
    </html>
  );
}
