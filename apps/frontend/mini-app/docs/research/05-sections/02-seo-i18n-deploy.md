# SEO, Интернационализация, Обработка ошибок, Мониторинг и Деплой

> Расширенное исследование для enterprise Next.js 15+ (2025-2026).
> Дополняет `05-auth-security-performance.md` (секции 6-12) деталями реализации.

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
  const total = await prisma.post.count({ where: { published: true } });
  return Array.from({ length: Math.ceil(total / 50000) }, (_, i) => ({ id: i }));
}

export default async function sitemap({ id }: { id: number }): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com';
  const posts = await prisma.post.findMany({
    where: { published: true },
    skip: id * 50000,
    take: 50000,
    select: { slug: true, updatedAt: true },
  });
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

Вставка в страницу (данные из БД, `JSON.stringify` экранирует спецсимволы):

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
    <div className="flex min-h-[400px] flex-col items-center justify-center">
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

## 5. Деплой и инфраструктура

### 5.1. Dockerfile — multi-stage standalone

```dockerfile
# Stage 1: deps
FROM node:22-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile --prod=false

# Stage 2: build
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_SENTRY_DSN
ARG NEXT_PUBLIC_APP_URL
ARG SENTRY_AUTH_TOKEN
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN \
    NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL \
    SENTRY_AUTH_TOKEN=$SENTRY_AUTH_TOKEN \
    NEXT_TELEMETRY_DISABLED=1
RUN corepack enable pnpm && pnpm build

# Stage 3: runner
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
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

### 5.3. docker-compose.yml

```yaml
version: '3.9'
services:
  app:
    build:
      { context: ., dockerfile: Dockerfile, args: { NEXT_PUBLIC_APP_URL: 'http://localhost:3000' } }
    ports: ['3000:3000']
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/myapp
      - REDIS_URL=redis://redis:6379
      - AUTH_SECRET=${AUTH_SECRET}
      - SENTRY_DSN=${SENTRY_DSN}
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    restart: unless-stopped
    deploy: { resources: { limits: { memory: 512M, cpus: '1.0' } } }

  db:
    image: postgres:17-alpine
    environment: { POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: myapp }
    volumes: [postgres_data:/var/lib/postgresql/data]
    ports: ['5432:5432']
    healthcheck:
      { test: ['CMD-SHELL', 'pg_isready -U postgres'], interval: 10s, timeout: 5s, retries: 5 }

  redis:
    image: redis:7-alpine
    ports: ['6379:6379']
    volumes: [redis_data:/data]
    healthcheck: { test: ['CMD', 'redis-cli', 'ping'], interval: 10s, timeout: 5s, retries: 5 }
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru

volumes:
  postgres_data:
  redis_data:
```

### 5.4. Kubernetes — Deployment, Service, HPA

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: nextjs-app }
spec:
  replicas: 3
  selector: { matchLabels: { app: nextjs-app } }
  template:
    metadata: { labels: { app: nextjs-app } }
    spec:
      containers:
        - name: nextjs
          image: registry.example.com/myapp:latest
          ports: [{ containerPort: 3000 }]
          env:
            - { name: NODE_ENV, value: 'production' }
            - {
                name: DATABASE_URL,
                valueFrom: { secretKeyRef: { name: app-secrets, key: database-url } },
              }
          resources:
            requests: { memory: '256Mi', cpu: '250m' }
            limits: { memory: '512Mi', cpu: '1000m' }
          readinessProbe:
            {
              httpGet: { path: /api/health, port: 3000 },
              initialDelaySeconds: 10,
              periodSeconds: 10,
            }
          livenessProbe:
            {
              httpGet: { path: /api/health, port: 3000 },
              initialDelaySeconds: 30,
              periodSeconds: 30,
            }
          lifecycle: { preStop: { exec: { command: ['sleep', '5'] } } }
      terminationGracePeriodSeconds: 30
---
apiVersion: v1
kind: Service
metadata: { name: nextjs-app }
spec:
  selector: { app: nextjs-app }
  ports: [{ port: 80, targetPort: 3000 }]
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: nextjs-app }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: nextjs-app }
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - {
        type: Resource,
        resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } },
      }
```

### 5.5. Shared ISR cache для multi-pod (Redis)

```typescript
// cache-handler.mjs
import { CacheHandler } from '@neshca/cache-handler';
import createRedisHandler from '@neshca/cache-handler/redis-strings';
import { createClient } from 'redis';

CacheHandler.onCreation(async () => {
  const client = createClient({ url: process.env.REDIS_URL });
  await client.connect();
  return { handlers: [createRedisHandler({ client })] };
});
export default CacheHandler;
```

```typescript
// next.config.ts — подключение cache handler
const nextConfig = {
  output: 'standalone',
  cacheHandler:
    process.env.NODE_ENV === 'production' ? require.resolve('./cache-handler.mjs') : undefined,
  cacheMaxMemorySize: 0, // Отключаем in-memory кэш
};
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

### Kubernetes

- [ ] readiness/liveness probes на `/api/health`
- [ ] `preStop` hook (`sleep 5`) для graceful shutdown
- [ ] HPA (min 2, max по нагрузке)
- [ ] Shared cache (Redis) для ISR
- [ ] `cacheMaxMemorySize: 0`
- [ ] Resource limits/requests

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
