import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// `next dev` всегда запускается с NODE_ENV='development', `next build|start` —
// с 'production'. Любое другое значение (или его отсутствие) трактуем как dev,
// чтобы случайный пустой env не ломал HMR на локальной машине разработчика.
const isProd = process.env.NODE_ENV === 'production';

// React Refresh / HMR в dev-сборке Next.js полагается на динамическое
// исполнение кода (через `unsafe-eval`). В production эта директива остаётся
// выключенной — там она не нужна и закрывает крупный вектор XSS-эскалации.
const devOnlyScriptSrc = isProd ? '' : " 'unsafe-eval'";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'Content-Security-Policy',
            // `unsafe-inline` for scripts is still required by Next.js' inline
            // bootstrap; switch to nonce-based CSP when adopting Next.js
            // proxy-driven nonces. The dev-only `unsafe-eval` allowance enables
            // React Refresh and is omitted from production builds.
            value: `default-src 'self'; script-src 'self' 'unsafe-inline'${devOnlyScriptSrc}; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob: https:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self';`,
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
        ],
      },
    ];
  },
  images: {
    remotePatterns: [{ protocol: 'https', hostname: '**' }],
  },
  webpack(config) {
    config.resolve.alias['@'] = path.resolve(__dirname, 'src');

    config.module.rules.push({
      test: /\.svg$/i,
      issuer: /\.[jt]sx?$/,
      use: ['@svgr/webpack'],
    });

    // Keep Next.js default splitChunks strategy to avoid overriding framework optimizations.
    return config;
  },
};

export default nextConfig;
