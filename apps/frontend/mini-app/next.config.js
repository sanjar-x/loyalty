const { detectLanIPv4 } = require('./scripts/detect-lan-ips');

// Dev vaqtida LAN dagi qurilmadan (Telegram Mini App, telefon, tablet) kirish uchun
// joriy kompyuterning barcha xususiy tarmoq IPv4 manzillari avtomatik aniqlanadi.
// DHCP IP o'zgartirsa — `npm run dev` ni qayta ishga tushirganda ro'yxat yangilanadi.
// Qo'shimcha origin'larni `EXTRA_DEV_ORIGINS=foo.local,bar.ngrok.app npm run dev`
// env orqali uzatish mumkin.
const STATIC_DEV_ORIGINS = ['localhost', '127.0.0.1'];
const detectedLanIPs = process.env.NODE_ENV === 'production' ? [] : detectLanIPv4();
const EXTRA_DEV_ORIGINS = (process.env.EXTRA_DEV_ORIGINS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

const allowedDevOrigins = [
  ...new Set([...STATIC_DEV_ORIGINS, ...detectedLanIPs, ...EXTRA_DEV_ORIGINS]),
];

if (process.env.NODE_ENV !== 'production' && detectedLanIPs.length > 0) {
  console.log(`[next.config] allowedDevOrigins → LAN auto: ${detectedLanIPs.join(', ')}`);
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins,
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 3600,
    deviceSizes: [640, 750, 828, 1080],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'image-backend-production-72e6.up.railway.app',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'loyality.t3.tigrisfiles.io',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: '*.tigrisfiles.io',
        pathname: '/**',
      },
    ],
  },
};

module.exports = nextConfig;
