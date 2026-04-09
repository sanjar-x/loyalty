# Аутентификация, безопасность и производительность -- детальная реализация

> Production-ready код для Next.js 15/16 + Auth.js v5. Апрель 2026.

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

### auth.ts -- полная конфигурация с Prisma-адаптером

```typescript
import NextAuth from 'next-auth';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { prisma } from '@/lib/prisma';
import authConfig from './auth.config';
import Credentials from 'next-auth/providers/credentials';
import { z } from 'zod';
import bcrypt from 'bcryptjs';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(128),
});

export const { handlers, signIn, signOut, auth } = NextAuth({
  adapter: PrismaAdapter(prisma),
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
        const user = await prisma.user.findUnique({
          where: { email: parsed.data.email },
          select: { id: true, email: true, name: true, role: true, hashedPassword: true },
        });
        if (!user?.hashedPassword) return null;
        const valid = await bcrypt.compare(parsed.data.password, user.hashedPassword);
        if (!valid) return null;
        return { id: user.id, email: user.email, name: user.name, role: user.role as any };
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
компонентов с обращением к БД, cookies, headers или динамическим fetch.

---

## 7. next/image и next/font -- оптимизация

### next/image

```tsx
import Image from 'next/image';

{
  /* LCP hero -- priority обязателен, максимум 1-2 на страницу */
}
<Image
  src="/hero.webp"
  alt="Hero"
  width={1200}
  height={600}
  priority
  sizes="100vw"
  quality={85}
  placeholder="blur"
  blurDataURL="data:image/jpeg;base64,..."
/>;

{
  /* Карточка -- lazy loading по умолчанию, sizes для responsive */
}
<Image
  src="/card.webp"
  alt="Card"
  width={400}
  height={300}
  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
/>;

{
  /* Fill-режим для контейнера с неизвестными размерами */
}
<div className="relative aspect-video">
  <Image src="/dynamic.webp" alt="" fill sizes="50vw" className="object-cover" />
</div>;
```

**Ключевое:** `priority` только для LCP. `sizes` обязателен для responsive.
AVIF (в next.config.ts `formats: ["image/avif", "image/webp"]`) на 20-30% легче WebP.

### next/font -- zero layout shift

```typescript
// app/layout.tsx
import { Inter, JetBrains_Mono } from "next/font/google";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-inter",
});

const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-mono",
  weight: ["400", "700"],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`${inter.variable} ${mono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

Шрифты загружаются в build-time и хостятся с вашего домена -- нет запросов к Google,
автоматический `size-adjust` исключает CLS.

---

## 8. Bundle Analyzer и оптимизация бандла

### Анализ

```bash
pnpm add -D @next/bundle-analyzer
ANALYZE=true pnpm build   # интерактивный отчёт в браузере
```

### optimizePackageImports

Решает проблему barrel-файлов (`index.ts` с реэкспортами). Без оптимизации
`import { Button } from "@/components"` затягивает все 100 компонентов.

```typescript
// next.config.ts -- experimental.optimizePackageImports
['lucide-react', 'date-fns', 'lodash-es', '@heroicons/react', '@radix-ui/react-icons'];
```

**Эффект:** до 90% ускорения hot reload, значительно меньше бандл.

### Dynamic imports

```typescript
"use client";
import dynamic from "next/dynamic";

const Chart = dynamic(() => import("@/components/chart"), {
  loading: () => <div className="h-96 animate-pulse bg-muted rounded-xl" />,
  ssr: false,
});
```

### Замена тяжёлых зависимостей

| Тяжёлая   | Размер | Замена                      | Размер   |
| --------- | ------ | --------------------------- | -------- |
| moment.js | ~290KB | date-fns                    | ~10-30KB |
| lodash    | ~530KB | lodash-es / нативные методы | ~5-20KB  |
| axios     | ~40KB  | fetch (встроен)             | 0KB      |
| uuid      | ~12KB  | crypto.randomUUID()         | 0KB      |

### Бюджет

First Load JS на маршруте не должен превышать **200KB** (gzip). `"use client"` только на
leaf-компонентах (кнопка, форма), не на layout-компонентах. Server Components по умолчанию
дают -65% клиентского бандла.

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
