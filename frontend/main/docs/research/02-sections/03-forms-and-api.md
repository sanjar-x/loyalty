# 4-5. Формы, валидация и архитектура API-слоя (углубленное исследование)

> Расширенный анализ React Hook Form, Zod, HTTP-клиентов и паттернов enterprise API layer.

---

## 4.1 React Hook Form: продвинутые паттерны

### Multi-step Form Wizard

```typescript
// components/multi-step-form.tsx
'use client';

import { useForm, FormProvider, useFormContext } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { z } from 'zod';

// Общая схема
const wizardSchema = z.object({
  // Step 1: Personal
  firstName: z.string().min(2),
  lastName: z.string().min(2),
  email: z.string().email(),
  // Step 2: Address
  street: z.string().min(5),
  city: z.string().min(2),
  zipCode: z.string().regex(/^\d{6}$/),
  // Step 3: Payment
  cardNumber: z.string().regex(/^\d{16}$/),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/),
});

type WizardData = z.infer<typeof wizardSchema>;

const STEPS = [
  { fields: ['firstName', 'lastName', 'email'] as const, title: 'Personal Info' },
  { fields: ['street', 'city', 'zipCode'] as const, title: 'Address' },
  { fields: ['cardNumber', 'expiry'] as const, title: 'Payment' },
];

export function MultiStepForm() {
  const [step, setStep] = useState(0);
  const methods = useForm<WizardData>({
    resolver: zodResolver(wizardSchema),
    mode: 'onTouched',
  });

  const nextStep = async () => {
    const fields = STEPS[step].fields;
    const valid = await methods.trigger(fields);
    if (valid) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const prevStep = () => setStep((s) => Math.max(s - 1, 0));

  const onSubmit = methods.handleSubmit(async (data) => {
    await submitWizard(data);
  });

  return (
    <FormProvider {...methods}>
      <form onSubmit={onSubmit}>
        <div>Step {step + 1} of {STEPS.length}: {STEPS[step].title}</div>

        {step === 0 && <PersonalStep />}
        {step === 1 && <AddressStep />}
        {step === 2 && <PaymentStep />}

        <div>
          {step > 0 && <button type="button" onClick={prevStep}>Back</button>}
          {step < STEPS.length - 1 && (
            <button type="button" onClick={nextStep}>Next</button>
          )}
          {step === STEPS.length - 1 && (
            <button type="submit">Submit</button>
          )}
        </div>
      </form>
    </FormProvider>
  );
}

function PersonalStep() {
  const { register, formState: { errors } } = useFormContext<WizardData>();
  return (
    <>
      <input {...register('firstName')} placeholder="First Name" />
      {errors.firstName && <span>{errors.firstName.message}</span>}
      <input {...register('lastName')} placeholder="Last Name" />
      <input {...register('email')} placeholder="Email" />
    </>
  );
}
```

### useFieldArray для динамических полей

```typescript
// components/invoice-form.tsx
'use client';

import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const lineItemSchema = z.object({
  description: z.string().min(1),
  quantity: z.coerce.number().min(1),
  unitPrice: z.coerce.number().min(0),
});

const invoiceSchema = z.object({
  clientName: z.string().min(2),
  items: z.array(lineItemSchema).min(1, 'At least one item required'),
});

type InvoiceData = z.infer<typeof invoiceSchema>;

export function InvoiceForm() {
  const { register, control, handleSubmit, watch } = useForm<InvoiceData>({
    resolver: zodResolver(invoiceSchema),
    defaultValues: {
      items: [{ description: '', quantity: 1, unitPrice: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'items',
  });

  const items = watch('items');
  const total = items?.reduce((sum, item) =>
    sum + (item.quantity || 0) * (item.unitPrice || 0), 0) || 0;

  return (
    <form onSubmit={handleSubmit(console.log)}>
      <input {...register('clientName')} placeholder="Client Name" />

      {fields.map((field, index) => (
        <div key={field.id}>
          <input {...register(`items.${index}.description`)} placeholder="Description" />
          <input {...register(`items.${index}.quantity`)} type="number" />
          <input {...register(`items.${index}.unitPrice`)} type="number" step="0.01" />
          {fields.length > 1 && (
            <button type="button" onClick={() => remove(index)}>Remove</button>
          )}
        </div>
      ))}

      <button type="button" onClick={() => append({ description: '', quantity: 1, unitPrice: 0 })}>
        Add Item
      </button>

      <div>Total: ${total.toFixed(2)}</div>
      <button type="submit">Create Invoice</button>
    </form>
  );
}
```

---

## 4.2 Продвинутые Zod-паттерны

### Discriminated Unions

```typescript
// schemas/payment.ts
import { z } from 'zod';

const creditCardSchema = z.object({
  method: z.literal('credit_card'),
  cardNumber: z.string().regex(/^\d{16}$/),
  expiry: z.string().regex(/^\d{2}\/\d{2}$/),
  cvv: z.string().regex(/^\d{3,4}$/),
});

const bankTransferSchema = z.object({
  method: z.literal('bank_transfer'),
  iban: z.string().min(15).max(34),
  bic: z.string().min(8).max(11),
});

const cryptoSchema = z.object({
  method: z.literal('crypto'),
  walletAddress: z.string().min(26).max(62),
  network: z.enum(['ethereum', 'bitcoin', 'solana']),
});

export const paymentSchema = z.discriminatedUnion('method', [
  creditCardSchema,
  bankTransferSchema,
  cryptoSchema,
]);

export type PaymentData = z.infer<typeof paymentSchema>;
```

### Transform и Preprocess

```typescript
// schemas/product.ts
import { z } from 'zod';

export const productSchema = z.object({
  name: z
    .string()
    .min(1)
    .transform((s) => s.trim()),

  // Preprocess: string из input -> number
  price: z.preprocess(
    (val) => (typeof val === 'string' ? parseFloat(val) : val),
    z.number().positive(),
  ),

  // Transform: cents для хранения
  priceInCents: z
    .number()
    .positive()
    .transform((val) => Math.round(val * 100)),

  // Refinement: кастомная валидация
  slug: z
    .string()
    .min(3)
    .regex(/^[a-z0-9-]+$/, 'Only lowercase letters, numbers, and hyphens')
    .refine(
      async (slug) => {
        const exists = await checkSlugExists(slug);
        return !exists;
      },
      { message: 'Slug already taken' },
    ),

  tags: z.array(z.string()).default([]),

  // Coerce: автоматическое приведение типов
  publishedAt: z.coerce.date(),
});
```

---

## 4.3 Conform.js: серверно-ориентированные формы

Альтернатива RHF для Server-Action-first подхода:

```typescript
// app/actions/contact.ts
'use server';

import { parseWithZod } from '@conform-to/zod';
import { contactSchema } from '@/schemas/contact';

export async function submitContact(prevState: unknown, formData: FormData) {
  const submission = parseWithZod(formData, { schema: contactSchema });

  if (submission.status !== 'success') {
    return submission.reply();
  }

  await db.contacts.create({ data: submission.value });
  return submission.reply({ resetForm: true });
}

// components/contact-form.tsx
'use client';

import { useForm } from '@conform-to/react';
import { parseWithZod } from '@conform-to/zod';
import { useActionState } from 'react';
import { submitContact } from '@/app/actions/contact';
import { contactSchema } from '@/schemas/contact';

export function ContactForm() {
  const [lastResult, action] = useActionState(submitContact, undefined);

  const [form, fields] = useForm({
    lastResult,
    onValidate({ formData }) {
      return parseWithZod(formData, { schema: contactSchema });
    },
    shouldValidate: 'onBlur',
    shouldRevalidate: 'onInput',
  });

  return (
    <form id={form.id} onSubmit={form.onSubmit} action={action}>
      <input name={fields.email.name} />
      <div>{fields.email.errors}</div>
      <button type="submit">Send</button>
    </form>
  );
}
```

| Критерий                | React Hook Form         | Conform                       |
| ----------------------- | ----------------------- | ----------------------------- |
| Подход                  | Client-first            | Server-first                  |
| Server Actions          | Через `startTransition` | Нативная интеграция           |
| Bundle size             | ~9 KB                   | ~5 KB                         |
| Progressive enhancement | Нет (нужен JS)          | Да (работает без JS)          |
| DevTools                | Да                      | Нет                           |
| Экосистема              | Огромная                | Малая                         |
| **Рекомендация**        | SPA, сложные формы      | Server Actions, простые формы |

---

## 5.1 API-клиент: продвинутая конфигурация

### ky с refresh token rotation

```typescript
// lib/api-client.ts
import ky from 'ky';

let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const res = await ky
    .post('/api/auth/refresh', {
      json: { refreshToken: getRefreshToken() },
    })
    .json<{ accessToken: string }>();

  setAccessToken(res.accessToken);
  return res.accessToken;
}

export const apiClient = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_URL,
  timeout: 15_000,
  retry: { limit: 2, methods: ['get'], statusCodes: [408, 500, 502, 503] },
  hooks: {
    beforeRequest: [
      async (request) => {
        let token = getAccessToken();

        if (isTokenExpired(token)) {
          if (!isRefreshing) {
            isRefreshing = true;
            refreshPromise = refreshAccessToken().finally(() => {
              isRefreshing = false;
              refreshPromise = null;
            });
          }
          token = await refreshPromise!;
        }

        request.headers.set('Authorization', `Bearer ${token}`);
      },
    ],
    afterResponse: [
      async (request, options, response) => {
        if (response.status === 401) {
          // Token was invalid even after refresh — force logout
          logout();
          window.location.href = '/login';
        }
      },
    ],
  },
});
```

### OpenAPI TypeScript code generation

Автоматическая типизация API из OpenAPI спецификации:

```bash
# Установка
pnpm add -D openapi-typescript openapi-fetch

# Генерация типов
pnpm openapi-typescript https://api.example.com/openapi.json -o src/types/api.d.ts
```

```typescript
// lib/api-client.ts
import createClient from 'openapi-fetch';
import type { paths } from '@/types/api';

export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL,
  headers: { Authorization: `Bearer ${getToken()}` },
});

// Использование — полная типобезопасность:
const { data, error } = await api.GET('/products/{id}', {
  params: { path: { id: '123' } },
});
// data автоматически типизирован на основе OpenAPI schema
```

---

## 5.2 Централизованная обработка ошибок

```typescript
// lib/errors.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public details?: Record<string, string[]>,
  ) {
    super(message);
    this.name = 'AppError';
  }

  get isUnauthorized() {
    return this.statusCode === 401;
  }
  get isForbidden() {
    return this.statusCode === 403;
  }
  get isNotFound() {
    return this.statusCode === 404;
  }
  get isValidation() {
    return this.statusCode === 422;
  }
  get isServerError() {
    return this.statusCode >= 500;
  }
}

// lib/handle-api-error.ts
import { toast } from 'sonner';
import { AppError } from './errors';

export function handleApiError(error: unknown) {
  if (error instanceof AppError) {
    if (error.isUnauthorized) {
      window.location.href = '/login';
      return;
    }
    if (error.isValidation && error.details) {
      Object.values(error.details)
        .flat()
        .forEach((msg) => toast.error(msg));
      return;
    }
    if (error.isServerError) {
      toast.error('Server error. Please try again later.');
      return;
    }
    toast.error(error.message);
    return;
  }

  toast.error('An unexpected error occurred');
}
```

### TanStack Query глобальный обработчик

```typescript
// lib/query-client.ts
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { handleApiError } from './handle-api-error';

export function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => handleApiError(error),
    }),
    mutationCache: new MutationCache({
      onError: (error) => handleApiError(error),
    }),
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error) => {
          if (error instanceof AppError && error.statusCode < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}
```

---

## 5.3 File Upload с прогрессом

```typescript
// lib/upload.ts
export async function uploadFile(
  file: File,
  onProgress: (percent: number) => void,
): Promise<{ url: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Upload failed')));

    const formData = new FormData();
    formData.append('file', file);

    xhr.open('POST', '/api/upload');
    xhr.setRequestHeader('Authorization', `Bearer ${getToken()}`);
    xhr.send(formData);
  });
}

// hooks/use-file-upload.ts
('use client');

import { useState, useCallback } from 'react';
import { uploadFile } from '@/lib/upload';

export function useFileUpload() {
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const upload = useCallback(async (file: File) => {
    setIsUploading(true);
    setProgress(0);
    try {
      const result = await uploadFile(file, setProgress);
      return result;
    } finally {
      setIsUploading(false);
    }
  }, []);

  return { upload, progress, isUploading };
}
```

---

## Источники

- [React Hook Form Documentation](https://react-hook-form.com/)
- [Zod Documentation](https://zod.dev/)
- [Conform Documentation](https://conform.guide/)
- [ky Documentation](https://github.com/sindresorhus/ky)
- [openapi-typescript + openapi-fetch](https://openapi-ts.dev/)
- [Next.js: How to create forms with Server Actions](https://nextjs.org/docs/app/guides/forms)
