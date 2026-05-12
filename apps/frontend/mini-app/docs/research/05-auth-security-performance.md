# Auth, безопасность, SEO, i18n, мониторинг и деплой (2025-2026)

> **Контекст проекта:** Frontend-only Next.js приложение, часть большой системы с отдельными
> бэкенд-сервисами. Next.js выступает как BFF (Backend for Frontend) / proxy-слой.
> Аутентификация проксируется к auth-сервису, БД и ORM — на стороне бэкенда.
>
> Production-ready код для Next.js 15/16 + Auth.js v5. Апрель 2026.

---

## Содержание

### Часть 1 — Аутентификация, безопасность и производительность

- [1. Auth.js v5 — полная настройка](#1-authjs-v5----полная-настройка)
- [2. RBAC через Middleware](#2-rbac-через-middleware)
- [3. Security Headers и CSP](#3-security-headers-и-csp-с-nonce)
- [4. Rate Limiting (Upstash Redis)](#4-rate-limiting-upstash-redis)
- [5. Unified Middleware](#5-unified-middleware----auth--csp--rate-limit)
- [6. Partial Prerendering (PPR)](#6-partial-prerendering-ppr)
- [7. Оптимизация (ссылки на 03/04)](#7-оптимизация-шрифты-изображения-бандл)

### Часть 2 — SEO, i18n, мониторинг и деплой

- [1. SEO и Metadata API](#1-seo-и-metadata-api--расширенные-паттерны)
- [2. Интернационализация (next-intl)](#2-интернационализация-next-intl--полная-настройка)
- [3. Обработка ошибок](#3-обработка-ошибок--расширенная-иерархия)
- [4. Мониторинг и Observability](#4-мониторинг-и-observability)
- [5. Деплой (Vercel)](#5-деплой-vercel)
- [6. Чеклист деплоя](#6-чеклист-деплоя)

---

# Часть 1 — Аутентификация, безопасность и производительность

---

## 1. Auth.js v5 -- полная настройка

### types/next-auth.d.ts -- расширение типов

```typescript
import { DefaultSession, DefaultUser } from 'next-auth';
import { DefaultJWT } from 'next-auth/jwt';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      role: 'admin' | 'manager' | 'user';
    } & DefaultSession['user'];
  }
  interface User extends DefaultUser {
    role: 'admin' | 'manager' | 'user';
  }
}

declare module 'next-auth/jwt' {
  interface JWT extends DefaultJWT {
    id: string;
    role: 'admin' | 'manager' | 'user';
  }
}
```

### auth.config.ts -- edge-совместимая конфигурация (без ORM/bcrypt)

```typescript
import type { NextAuthConfig } from 'next-auth';
import GitHub from 'next-auth/providers/github';
import Google from 'next-auth/providers/google';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
});

export default {
  providers: [
    GitHub({ clientId: process.env.AUTH_GITHUB_ID, clientSecret: process.env.AUTH_GITHUB_SECRET }),
    Google({ clientId: process.env.AUTH_GOOGLE_ID, clientSecret: process.env.AUTH_GOOGLE_SECRET }),
    Credentials({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      authorize: async (credentials) => {
        const parsed = loginSchema.safeParse(credentials);
        if (!parsed.success) return null;
        // Реальная проверка пароля -- в auth.ts (Node.js runtime, bcrypt доступен)
        return null;
      },
    }),
  ],
  pages: { signIn: '/login', error: '/auth/error' },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isProtected = ['/dashboard', '/admin', '/settings'].some((p) =>
        nextUrl.pathname.startsWith(p),
      );
      if (isProtected && !isLoggedIn) {
        const url = new URL('/login', nextUrl);
        url.searchParams.set('callbackUrl', nextUrl.pathname);
        return Response.redirect(url);
      }
      if (isLoggedIn && nextUrl.pathname === '/login') {
        return Response.redirect(new URL('/dashboard', nextUrl));
      }
      return true;
    },
    jwt({ token, user }) {
      if (user) {
        token.id = user.id!;
        token.role = user.role;
      }
      return token;
    },
    session({ session, token }) {
      session.user.id = token.id;
      session.user.role = token.role;
      return session;
    },
  },
} satisfies NextAuthConfig;
```

### auth.ts -- конфигурация с proxy к auth-сервису (BFF)

> **Примечание BFF:** в нашей архитектуре нет прямого доступа к БД из Next.js.
> Вместо PrismaAdapter credentials-авторизация проксируется к auth-сервису.
> OAuth-провайдеры (GitHub, Google) обрабатываются Auth.js с JWT-стратегией (без DB adapter).

```typescript
import NextAuth from 'next-auth';
import authConfig from './auth.config';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
});

export const { handlers, signIn, signOut, auth } = NextAuth({
  // Без adapter — JWT-only стратегия (не нужна БД для сессий)
  session: { strategy: 'jwt', maxAge: 30 * 24 * 60 * 60 },
  ...authConfig,
  providers: [
    ...authConfig.providers.filter((p) => (p as { id?: string }).id !== 'credentials'),
    Credentials({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      authorize: async (credentials) => {
        const parsed = loginSchema.safeParse(credentials);
        if (!parsed.success) return null;

        // Proxy к auth-сервису — проверка пароля на стороне бэкенда
        const res = await fetch(`${process.env.AUTH_SERVICE_URL}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed.data),
        });

        if (!res.ok) return null;
        const user = await res.json();
        return { id: user.id, email: user.email, name: user.name, role: user.role };
      },
    }),
  ],
  events: {
    async signIn({ user, account }) {
      console.log(`[AUTH] Sign in: ${user.email} via ${account?.provider}`);
    },
  },
});
```

### Route Handler

```typescript
// app/api/auth/[...nextauth]/route.ts
import { handlers } from '@/auth';
export const { GET, POST } = handlers;
```

---

## 2. RBAC через Middleware

### Конфигурация ролей

```typescript
// lib/rbac.ts
export type Role = 'admin' | 'manager' | 'user';

const protectedRoutes: { path: string; roles: Role[] }[] = [
  { path: '/admin', roles: ['admin'] },
  { path: '/api/admin', roles: ['admin'] },
  { path: '/settings/billing', roles: ['admin', 'manager'] },
  { path: '/settings', roles: ['admin', 'manager', 'user'] },
  { path: '/dashboard', roles: ['admin', 'manager', 'user'] },
];

export function hasAccess(pathname: string, userRole: Role | undefined): boolean {
  const route = protectedRoutes.find((r) => pathname.startsWith(r.path));
  if (!route) return true;
  if (!userRole) return false;
  return route.roles.includes(userRole);
}
```

### Серверная проверка в компонентах и API

```typescript
// lib/auth-guard.ts
import { auth } from '@/auth';
import { redirect } from 'next/navigation';
import type { Role } from '@/lib/rbac';

export async function requireRole(roles: Role[]) {
  const session = await auth();
  if (!session?.user) redirect('/login');
  if (!roles.includes(session.user.role)) redirect('/unauthorized');
  return session;
}
```

```typescript
// app/admin/page.tsx
import { requireRole } from "@/lib/auth-guard";

export default async function AdminPage() {
  const session = await requireRole(["admin"]);
  return <h1>Admin: {session.user.name}</h1>;
}
```

```typescript
// app/api/admin/users/route.ts
import { auth } from '@/auth';
import { NextResponse } from 'next/server';

export async function GET() {
  const session = await auth();
  if (!session || session.user.role !== 'admin') {
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }
  return NextResponse.json({ users: [] });
}
```

---

## 3. Security Headers и CSP с nonce

### Генерация CSP

```typescript
// lib/security-headers.ts
export function generateCSP(nonce: string) {
  return [
    `default-src 'self'`,
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}'`,
    `img-src 'self' blob: data: https:`,
    `font-src 'self'`,
    `connect-src 'self' https://vitals.vercel-insights.com`,
    `object-src 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `frame-ancestors 'none'`,
    `upgrade-insecure-requests`,
  ].join('; ');
}

export const securityHeaders = [
  { key: 'X-DNS-Prefetch-Control', value: 'on' },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(), browsing-topics=()',
  },
];
```

### next.config.ts -- полная конфигурация

```typescript
import type { NextConfig } from 'next';
import { securityHeaders } from './lib/security-headers';
import bundleAnalyzer from '@next/bundle-analyzer';

const withBundleAnalyzer = bundleAnalyzer({ enabled: process.env.ANALYZE === 'true' });

const nextConfig: NextConfig = {
  experimental: {
    ppr: true,
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-icons',
      'date-fns',
      'lodash-es',
      '@heroicons/react',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-tooltip',
    ],
  },
  output: 'standalone',
  async headers() {
    return [{ source: '/(.*)', headers: securityHeaders }];
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 30,
    remotePatterns: [
      { protocol: 'https', hostname: 'images.example.com', pathname: '/uploads/**' },
    ],
  },
};

export default withBundleAnalyzer(nextConfig);
```

---

## 4. Rate Limiting (Upstash Redis)

```typescript
// lib/rate-limit.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { NextRequest, NextResponse } from 'next/server';

const limiters = {
  api: new Ratelimit({
    redis: Redis.fromEnv(),
    limiter: Ratelimit.slidingWindow(20, '10 s'),
    prefix: 'rl:api',
  }),
  auth: new Ratelimit({
    redis: Redis.fromEnv(),
    limiter: Ratelimit.slidingWindow(5, '60 s'),
    prefix: 'rl:auth',
  }),
};

export async function applyRateLimit(request: NextRequest) {
  const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ?? '127.0.0.1';
  const type = request.nextUrl.pathname.startsWith('/api/auth') ? 'auth' : 'api';
  const { success, limit, reset, remaining } = await limiters[type].limit(ip);

  if (!success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      {
        status: 429,
        headers: {
          'X-RateLimit-Limit': limit.toString(),
          'X-RateLimit-Remaining': '0',
          'Retry-After': Math.ceil((reset - Date.now()) / 1000).toString(),
        },
      },
    );
  }
  return null;
}
```

---

## 5. Unified Middleware -- Auth + CSP + Rate Limit

Next.js поддерживает только один `middleware.ts`. Порядок: Rate limit -> CSP nonce -> Auth/RBAC.

> **Next.js 16:** `middleware.ts` переименован в `proxy.ts`.

```typescript
// middleware.ts (Next.js 15) или proxy.ts (Next.js 16)
import { NextRequest, NextResponse } from 'next/server';
import NextAuth from 'next-auth';
import authConfig from './auth.config';
import { hasAccess, type Role } from './lib/rbac';
import { generateCSP } from './lib/security-headers';
import { applyRateLimit } from './lib/rate-limit';

const { auth } = NextAuth(authConfig);

export default auth(async (req) => {
  const { pathname } = req.nextUrl;

  // 1. Rate Limiting (API)
  if (pathname.startsWith('/api')) {
    const blocked = await applyRateLimit(req);
    if (blocked) return blocked;
  }

  // 2. RBAC
  const userRole = req.auth?.user?.role as Role | undefined;
  if (!hasAccess(pathname, userRole)) {
    if (!req.auth?.user) {
      const url = new URL('/login', req.nextUrl);
      url.searchParams.set('callbackUrl', pathname);
      return NextResponse.redirect(url);
    }
    return NextResponse.redirect(new URL('/unauthorized', req.nextUrl));
  }

  // 3. CSP nonce
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const csp = generateCSP(nonce);
  const headers = new Headers(req.headers);
  headers.set('x-nonce', nonce);
  headers.set('Content-Security-Policy', csp);

  const response = NextResponse.next({ request: { headers } });
  response.headers.set('Content-Security-Policy', csp);
  return response;
});

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon\\.ico|sitemap\\.xml|robots\\.txt|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
  ],
};
```

### CVE-2025-29927 -- обход middleware (CVSS 9.1)

Инъекция заголовка `x-middleware-subrequest` позволяла полностью обойти middleware.
Затронуты Next.js 11.1.4--15.2.2. **Обязательно** обновить до 14.2.25+ / 15.2.3+.

---

## 6. Partial Prerendering (PPR)

PPR отдаёт статический HTML-shell мгновенно с CDN, а динамические блоки в `<Suspense>`
стримятся параллельно. Один HTTP-запрос, минимальный TTFB.

> **Next.js 16:** PPR стабилен с Cache Components, флаг `experimental.ppr` больше не нужен.

```typescript
// app/dashboard/page.tsx
import { Suspense } from "react";
import { UserStats } from "@/components/dashboard/user-stats";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  return (
    <>
      {/* Статика -- мгновенно с CDN */}
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <nav>{/* навигация, layout */}</nav>

      {/* Динамика -- стримится */}
      <Suspense fallback={<Skeleton className="h-32" />}>
        <UserStats />
      </Suspense>
      <Suspense fallback={<Skeleton className="h-64" />}>
        <RecentActivity />
      </Suspense>
    </>
  );
}
```

**Правило:** всё, что может быть статическим -- должно быть. `<Suspense>` только для
компонентов с обращением к бэкенд-сервисам, cookies, headers или динамическим fetch.

---

## 7. Оптимизация: шрифты, изображения, бандл

> Детальные руководства по next/image и next/font — в `03-ui-design-system.md` (Часть 5, секции 10-11).
> Bundle Analyzer и инструменты мониторинга — в `04-dx-tooling.md` (Часть 3, секция 4).

**Ключевые правила:**

- `priority` только для LCP-изображения (1-2 на страницу)
- `sizes` обязателен для responsive images
- AVIF (`formats: ["image/avif", "image/webp"]`) на 20-30% легче WebP
- `next/font` с `display: "swap"` — zero CLS
- First Load JS бюджет: **< 200KB** gzip на маршрут
- `"use client"` только на leaf-компонентах

---

## Источники

- [Auth.js v5 -- Installation](https://authjs.dev/getting-started/installation)
- [Auth.js v5 -- Middleware](https://authjs.dev/reference/nextjs/middleware)
- [Auth.js -- RBAC Guide](https://authjs.dev/guides/role-based-access-control)
- [Next.js -- CSP Guide](https://nextjs.org/docs/app/guides/content-security-policy)
- [Next.js -- PPR](https://nextjs.org/docs/15/app/getting-started/partial-prerendering)
- [Next.js 16 Blog](https://nextjs.org/blog/next-16)
- [Next.js Security 2025](https://www.turbostarter.dev/blog/complete-nextjs-security-guide-2025-authentication-api-protection-and-best-practices)
- [Next.js Security 2026](https://www.authgear.com/post/nextjs-security-best-practices)
- [Next.js Performance 2026](https://dev.to/bean_bean/nextjs-performance-optimization-the-2026-complete-guide-1a9k)
- [RBAC in Next.js 15](https://www.jigz.dev/blogs/how-to-use-middleware-for-role-based-access-control-in-next-js-15-app-router)
- [CVE-2025-29927](https://www.averlon.ai/blog/nextjs-cve-2025-29927-header-injection)
- [Vercel: optimizePackageImports](https://vercel.com/blog/how-we-optimized-package-imports-in-next-js)

---

---

# Часть 2 — SEO, i18n, мониторинг и деплой

> Enterprise Next.js 15+ (2025-2026).

---

## 1. SEO и Metadata API — расширенные паттерны

### 1.1. Статические метаданные с полным OG/Twitter

```typescript
// app/layout.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  metadataBase: new URL('https://example.com'),
  title: { default: 'My App', template: '%s | My App' },
  description: 'Enterprise-платформа нового поколения',
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    alternateLocale: ['en_US', 'kk_KZ'],
    siteName: 'My App',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'My App' }],
  },
  twitter: { card: 'summary_large_image', creator: '@myapp' },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: { google: 'g-token', yandex: 'y-token' },
};
```

### 1.2. generateMetadata с alternates для i18n

```typescript
// app/blog/[slug]/page.tsx
import type { Metadata } from 'next';

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return {};

  return {
    title: post.title,
    description: post.excerpt,
    openGraph: {
      type: 'article',
      publishedTime: post.publishedAt,
      modifiedTime: post.updatedAt,
      authors: [post.author.name],
      images: [{ url: post.ogImage, width: 1200, height: 630 }],
    },
    alternates: {
      canonical: `/blog/${slug}`,
      languages: { ru: `/blog/${slug}`, en: `/en/blog/${slug}` },
    },
  };
}
```

### 1.3. Множественные sitemap для больших сайтов (>50K URL)

```typescript
// app/sitemap.ts
import type { MetadataRoute } from 'next';

export async function generateSitemaps() {
  // Запрос к бэкенд-сервису за общим количеством
  const { total } = await apiServer.get<{ total: number }>('/posts/count?published=true');
  return Array.from({ length: Math.ceil(total / 50000) }, (_, i) => ({ id: i }));
}

export default async function sitemap({ id }: { id: number }): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com';
  const posts = await apiServer.get<{ slug: string; updatedAt: string }[]>(
    `/posts?published=true&skip=${id * 50000}&take=50000&fields=slug,updatedAt`,
  );
  return posts.map((p) => ({ url: `${baseUrl}/blog/${p.slug}`, lastModified: p.updatedAt }));
}
```

### 1.4. robots.ts с блокировкой AI-краулеров

```typescript
// app/robots.ts
import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/api/', '/admin/', '/dashboard/', '/auth/'] },
      { userAgent: 'GPTBot', disallow: '/' },
    ],
    sitemap: 'https://example.com/sitemap.xml',
  };
}
```

### 1.5. JSON-LD — типобезопасные хелперы

```typescript
// lib/seo/json-ld.ts
type ArticleJsonLd = {
  title: string;
  description: string;
  publishedAt: string;
  updatedAt: string;
  authorName: string;
  image: string;
  url: string;
};

export function generateArticleJsonLd(a: ArticleJsonLd) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: a.title,
    description: a.description,
    datePublished: a.publishedAt,
    dateModified: a.updatedAt,
    author: { '@type': 'Person', name: a.authorName },
    image: a.image,
    url: a.url,
    publisher: {
      '@type': 'Organization',
      name: 'My App',
      logo: { '@type': 'ImageObject', url: 'https://example.com/logo.png' },
    },
  };
}
```

Вставка в страницу (`JSON.stringify` экранирует спецсимволы):

```tsx
const jsonLd = generateArticleJsonLd({
  /* ... */
});
return (
  <>
    <script type="application/ld+json" suppressHydrationWarning>
      {JSON.stringify(jsonLd)}
    </script>
    <article>{/* ... */}</article>
  </>
);
```

---

## 2. Интернационализация (next-intl) — полная настройка

next-intl — стандарт i18n для App Router (2025-2026). Бандл ~2KB, Server Components,
типобезопасные ключи, middleware-маршрутизация.

### 2.1. Структура проекта

```
├── i18n/
│   ├── routing.ts          # Конфигурация локалей
│   ├── request.ts          # Загрузка сообщений
│   └── navigation.ts       # Типобезопасные Link, redirect
├── messages/
│   ├── ru.json
│   └── en.json
├── middleware.ts
└── app/[locale]/layout.tsx
```

### 2.2. Конфигурация маршрутизации

```typescript
// i18n/routing.ts
import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['ru', 'en', 'kk'],
  defaultLocale: 'ru',
  localePrefix: 'as-needed', // /about (ru), /en/about (en)
  localeCookie: { name: 'NEXT_LOCALE', maxAge: 60 * 60 * 24 * 365 },
  localeDetection: true,
});

export type Locale = (typeof routing.locales)[number];
```

### 2.3. Навигация, загрузка сообщений, плагин

```typescript
// i18n/navigation.ts
import { createNavigation } from 'next-intl/navigation';
import { routing } from './routing';
export const { Link, redirect, usePathname, useRouter } = createNavigation(routing);
```

```typescript
// i18n/request.ts
import { getRequestConfig } from 'next-intl/server';
import { routing } from './routing';

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !routing.locales.includes(locale as any)) {
    locale = routing.defaultLocale;
  }
  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
    timeZone: 'Asia/Almaty',
  };
});
```

```typescript
// next.config.ts
import createNextIntlPlugin from 'next-intl/plugin';
const withNextIntl = createNextIntlPlugin('./i18n/request.ts');
export default withNextIntl({ output: 'standalone' });
```

### 2.4. Middleware (i18n + Auth.js)

```typescript
// middleware.ts — только i18n
import createMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

export default createMiddleware(routing);
export const config = { matcher: ['/((?!api|trpc|_next|_vercel|.*\\..*).*)'] };
```

Совмещение с Auth.js:

```typescript
// middleware.ts — i18n + авторизация
import { auth } from '@/auth';
import createIntlMiddleware from 'next-intl/middleware';
import { routing } from './i18n/routing';

const intlMiddleware = createIntlMiddleware(routing);

export default auth((req) => {
  const response = intlMiddleware(req);
  if (req.nextUrl.pathname.includes('/dashboard') && !req.auth) {
    return Response.redirect(new URL('/auth/signin', req.url));
  }
  return response;
});

export const config = { matcher: ['/((?!api|trpc|_next|_vercel|.*\\..*).*)'] };
```

### 2.5. Layout с локалью

```tsx
// app/[locale]/layout.tsx
import { notFound } from 'next/navigation';
import { getMessages, setRequestLocale } from 'next-intl/server';
import { NextIntlClientProvider } from 'next-intl';
import { routing } from '@/i18n/routing';

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as any)) notFound();
  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

### 2.6. Использование: Server / Client Components

```tsx
// Server Component — useTranslations из next-intl
import { useTranslations } from 'next-intl';
import { setRequestLocale } from 'next-intl/server';

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  setRequestLocale((await params).locale);
  const t = useTranslations('HomePage');
  return <h1>{t('title')}</h1>;
}
```

```tsx
// Client Component — тот же API
'use client';
import { useTranslations } from 'next-intl';
export function Counter() {
  const t = useTranslations('Counter');
  return <button>{t('increment')}</button>;
}
```

### 2.7. SEO для мультиязычного сайта

```typescript
// app/[locale]/layout.tsx — alternates для hreflang
export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return {
    alternates: {
      canonical: locale === 'ru' ? '/' : `/${locale}`,
      languages: { ru: '/', en: '/en', kk: '/kk' },
    },
  };
}
```

---

## 3. Обработка ошибок — расширенная иерархия

### 3.1. error.tsx с i18n и Sentry

```tsx
// app/[locale]/dashboard/error.tsx
'use client';
import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';
import { useTranslations } from 'next-intl';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('Common');
  useEffect(() => {
    Sentry.captureException(error, { tags: { boundary: 'dashboard' } });
  }, [error]);

  return (
    <div className="flex min-h-100 flex-col items-center justify-center">
      <h2 className="text-2xl font-bold">{t('error')}</h2>
      <p className="mt-2 text-gray-500">{error.digest ? `ID: ${error.digest}` : error.message}</p>
      <button onClick={reset} className="mt-4 rounded bg-blue-600 px-4 py-2 text-white">
        {t('tryAgain')}
      </button>
    </div>
  );
}
```

### 3.2. not-found.tsx с i18n

```tsx
// app/[locale]/not-found.tsx
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';

export default function NotFound() {
  const t = useTranslations('Common');
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center">
      <h1 className="text-6xl font-bold text-gray-300">404</h1>
      <p className="mt-4 text-lg">{t('notFound')}</p>
      <Link href="/" className="mt-6 text-blue-600 hover:underline">
        {t('backHome')}
      </Link>
    </div>
  );
}
```

---

## 4. Мониторинг и Observability

### 4.1. Sentry v8+ — полная конфигурация

**Файлы:** `instrumentation.ts`, `instrumentation-client.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`.

```typescript
// instrumentation.ts
import * as Sentry from '@sentry/nextjs';

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') await import('./sentry.server.config');
  if (process.env.NEXT_RUNTIME === 'edge') await import('./sentry.edge.config');
}
export const onRequestError = Sentry.captureRequestError;
```

```typescript
// instrumentation-client.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [
    Sentry.replayIntegration({ maskAllText: true, blockAllMedia: true }),
    Sentry.feedbackIntegration({ colorScheme: 'system', autoInject: false }),
  ],
  enableLogs: true,
});
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
```

```typescript
// sentry.server.config.ts
import * as Sentry from '@sentry/nextjs';
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 0.1,
  profilesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
});
```

**next.config.ts с Sentry + next-intl:**

```typescript
import { withSentryConfig } from '@sentry/nextjs';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');

export default withSentryConfig(withNextIntl({ output: 'standalone' }), {
  org: 'my-org',
  project: 'my-app',
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.CI,
  hideSourceMaps: true,
  tunnelRoute: '/monitoring', // Обход блокировщиков рекламы
  disableLogger: true,
  autoInstrumentServerFunctions: true,
  autoInstrumentMiddleware: true,
  autoInstrumentAppDirectory: true,
});
```

### 4.2. OpenTelemetry — два варианта

**Быстрый старт (@vercel/otel):**

```typescript
// instrumentation.ts
import { registerOTel } from '@vercel/otel';
export function register() {
  registerOTel({ serviceName: 'my-nextjs-app' });
}
```

**Ручная настройка (OTLP для Grafana/Jaeger):**

```typescript
// instrumentation.ts
export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { NodeSDK } = await import('@opentelemetry/sdk-node');
    const { Resource } = await import('@opentelemetry/resources');
    const { ATTR_SERVICE_NAME } = await import('@opentelemetry/semantic-conventions');
    const { OTLPTraceExporter } = await import('@opentelemetry/exporter-trace-otlp-http');
    const { OTLPMetricExporter } = await import('@opentelemetry/exporter-metrics-otlp-http');
    const { PeriodicExportingMetricReader } = await import('@opentelemetry/sdk-metrics');

    const sdk = new NodeSDK({
      resource: new Resource({ [ATTR_SERVICE_NAME]: 'my-nextjs-app' }),
      traceExporter: new OTLPTraceExporter({
        url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT + '/v1/traces',
      }),
      metricReader: new PeriodicExportingMetricReader({
        exporter: new OTLPMetricExporter({
          url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT + '/v1/metrics',
        }),
        exportIntervalMillis: 30000,
      }),
    });
    sdk.start();
  }
}
```

### 4.3. Pino — структурированные логи

```typescript
// lib/logger.ts
import pino from 'pino';

export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport:
    process.env.NODE_ENV === 'development'
      ? { target: 'pino-pretty', options: { colorize: true } }
      : undefined,
  formatters: { level: (label) => ({ level: label }) },
  timestamp: pino.stdTimeFunctions.isoTime,
  base: { service: 'my-nextjs-app', env: process.env.NODE_ENV },
});

export const createLogger = (module: string) => logger.child({ module });
```

---

## 5. Деплой (Vercel)

Проект деплоится на Vercel. Кэширование, CDN, serverless functions — управляются платформой.

### 5.1. Vercel-специфичная конфигурация

```typescript
// next.config.ts — ключевые настройки для Vercel
const nextConfig: NextConfig = {
  // НЕ нужен output: "standalone" для Vercel
  // Vercel автоматически оптимизирует деплой
};
```

### 5.2. Health check endpoint

```typescript
// app/api/health/route.ts
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const health = {
    status: 'ok' as 'ok' | 'degraded',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: process.env.APP_VERSION || 'unknown',
  };
  return NextResponse.json(health, { status: health.status === 'ok' ? 200 : 503 });
}
```

---

## 6. Чеклист деплоя

### Инфраструктура

- [ ] `output: "standalone"` в next.config.ts
- [ ] Multi-stage Dockerfile, non-root user, `CMD ["node", "server.js"]`
- [ ] `.dockerignore` исключает node_modules, .next, .env\*, .git
- [ ] Health check `/api/health` отвечает 200
- [ ] Секреты в env-переменных / K8s Secrets, не в коде
- [ ] `NEXT_PUBLIC_*` переданы как build args

### Мониторинг

- [ ] Sentry DSN: клиент + сервер + edge
- [ ] `onRequestError` в instrumentation.ts
- [ ] OpenTelemetry (трейсы + метрики)
- [ ] Pino: JSON-логи в production
- [ ] Session Replay (10% сессий, 100% с ошибками)

### SEO

- [ ] `metadata`/`generateMetadata` на публичных страницах
- [ ] `sitemap.ts` + `robots.ts`
- [ ] JSON-LD на ключевых страницах
- [ ] OG images 1200x630
- [ ] `alternates.canonical` + `alternates.languages`

### i18n

- [ ] next-intl middleware определяет локаль
- [ ] `generateStaticParams` возвращает все локали
- [ ] `setRequestLocale()` в каждом layout/page
- [ ] Полные переводы для всех языков

---

> **Источники:**
>
> - [next-intl -- App Router Setup](https://next-intl.dev/docs/getting-started/app-router)
> - [next-intl -- Routing Setup](https://next-intl.dev/docs/routing/setup)
> - [next-intl Guide 2025](https://www.buildwithmatija.com/blog/nextjs-internationalization-guide-next-intl-2025)
> - [next-intl Tutorial 2026](https://intlpull.com/blog/next-intl-complete-guide-2026)
> - [Next.js -- JSON-LD Guide](https://nextjs.org/docs/app/guides/json-ld)
> - [Next.js SEO: Metadata API + Structured Data](https://eastondev.com/blog/en/posts/dev/20251219-nextjs-seo-guide/)
> - [SEO in Next.js 16](https://jsdevspace.substack.com/p/how-to-configure-seo-in-nextjs-16)
> - [Sentry -- Next.js Manual Setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/)
> - [Sentry -- v8 to v9 Migration](https://docs.sentry.io/platforms/javascript/guides/nextjs/migration/v8-to-v9/)
> - [Next.js -- Deploying](https://nextjs.org/docs/app/getting-started/deploying)
> - [Next.js Docker (2026)](https://oneuptime.com/blog/post/2026-01-24-nextjs-docker-configuration/view)
> - [Docker Docs -- Next.js](https://docs.docker.com/guides/nextjs/)
> - [Next.js + K8s Optimization](https://blogs.businesscompassllc.com/2025/09/optimizing-nextjs-for-docker-and.html)
> - [Next.js -- OpenTelemetry](https://nextjs.org/docs/app/guides/open-telemetry)
> - [OTel + @vercel/otel (2026)](https://oneuptime.com/blog/post/2026-02-06-opentelemetry-nextjs-vercel-otel/view)
> - [Node.js Observability 2026](https://dev.to/axiom_agent/the-nodejs-observability-stack-in-2026-opentelemetry-prometheus-and-distributed-tracing-229b)
