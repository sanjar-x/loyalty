import { createEnv } from '@t3-oss/env-nextjs';
import { z } from 'zod';

export const env = createEnv({
  server: {
    API_BASE_URL: z.string().url().optional(),
    BACKEND_API_BASE_URL: z.string().url(),
    AUTH_SECRET: z.string().min(32).optional(),
    BROWSER_DEBUG_AUTH: z.enum(['true', 'false', '1', '0']).optional(),
    COOKIE_DOMAIN: z.string().optional(),
    DADATA_TOKEN: z.string().optional(),
    DADATA_SECRET: z.string().optional(),
    NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  },
  client: {
    NEXT_PUBLIC_APP_URL: z.string().url().default('http://localhost:3000'),
    NEXT_PUBLIC_BROWSER_DEBUG_AUTH: z.enum(['true', 'false', '1', '0']).optional(),
  },
  runtimeEnv: {
    API_BASE_URL: process.env.API_BASE_URL,
    BACKEND_API_BASE_URL: process.env.BACKEND_API_BASE_URL,
    AUTH_SECRET: process.env.AUTH_SECRET,
    BROWSER_DEBUG_AUTH: process.env.BROWSER_DEBUG_AUTH,
    COOKIE_DOMAIN: process.env.COOKIE_DOMAIN,
    DADATA_TOKEN: process.env.DADATA_TOKEN,
    DADATA_SECRET: process.env.DADATA_SECRET,
    NODE_ENV: process.env.NODE_ENV,
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
    NEXT_PUBLIC_BROWSER_DEBUG_AUTH: process.env.NEXT_PUBLIC_BROWSER_DEBUG_AUTH,
  },
  skipValidation: process.env.SKIP_ENV_VALIDATION === 'true',
});
