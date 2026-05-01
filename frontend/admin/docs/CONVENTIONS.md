# Соглашения по коду — `frontend/admin`

Контракт команды. PR не пройдёт ревью при нарушении.

## Имена

| Что                      | Стиль              | Пример                                      |
| ------------------------ | ------------------ | ------------------------------------------- |
| Файлы UI-компонентов     | `PascalCase.jsx`   | `ProductRow.jsx`, `OrderCard.jsx`           |
| Файлы хуков, утилит, API | `camelCase.js`     | `useAuth.jsx`, `formatCurrency.js`          |
| Папки слайсов            | `kebab-case`       | `product-form`, `order-filter`              |
| CSS Modules              | `<имя>.module.css` | `page.module.css`, `productForm.module.css` |
| SVG-иконки               | `kebab-case.svg`   | `arrow-left.svg`, `more-dots.svg`           |
| Mock-only API            | `<name>.mock.js`   | `orders.mock.js`                            |

## Импорты

- **Только через barrel `index.js`** для слайсов `entities/*`, `features/*`. Deep-paths запрещены, ESLint завалит билд.
- Server-only entry для category: `@/entities/category/server`.
- Алиас `@/*` → `src/*`.
- Порядок импортов: сторонние → `@/shared` → `@/entities` → `@/features` → `@/widgets` → относительные.

## Стили

Решение принимается так:

| Кейс                                | Решение                                                  |
| ----------------------------------- | -------------------------------------------------------- |
| Layout, spacing, цвет, hover        | Tailwind + дизайн-токены `app-*`                         |
| Условные классы                     | `cn()` из `@/shared/lib/utils`                           |
| Сложный grid, keyframes, page-shell | CSS Modules (`*.module.css`)                             |
| Inline `style={{...}}`              | только для динамических значений (progress %, transform) |

```jsx
// ✓ ОК
import { cn } from '@/shared/lib/utils';
<button className={cn('rounded-lg px-3 py-2', isActive && 'bg-app-text text-white')} />

// ✗ Не делать
<button className={clsx(...)} />            // используй cn
<div style={{ padding: '12px' }} />          // используй p-3
<div className="bg-[#22252b]" />             // используй bg-app-text
```

Дизайн-токены `app-*` определены в `tailwind.config.js`:
`app-bg`, `app-panel`, `app-border`, `app-text`, `app-muted`, `app-sidebar`, `app-success`, `app-danger`, `app-card`, `app-text-dark`, `app-text-secondary`, `app-divider`, `app-sidebar-text`, `app-badge-china`, `app-badge-china-text`.

## i18n entity-данных

Все `*I18N`-поля — объекты `{ ru, en }`:

```js
// Чтение
import { i18n } from '@/shared/lib/utils';
const label = i18n(product.titleI18N);

// Запись
import { buildI18nPayload } from '@/shared/lib/utils';
const payload = { titleI18N: buildI18nPayload(titleRu, titleEn) };
```

`buildI18nPayload(ru, '')` → `{ ru, en: ru }` (en обязателен на бэке).

## Даты

Только через `@/shared/lib/dayjs` (preconfigured, ru locale, plugins).

```js
import dayjs from '@/shared/lib/dayjs';
import { formatDateTime } from '@/shared/lib/utils';

formatDateTime(order.createdAt); // → "5 марта 14:32"
```

## Деньги

Backend хранит amount в **kopecks** (минимальные единицы валюты). На UI:

```js
import { formatCurrency } from '@/shared/lib/utils';

formatCurrency(amount / 100); // → "12 990 ₽"
```

## Иконки

```jsx
import ChevronIcon from '@/assets/icons/chevron.svg';

// SVG должны использовать fill="currentColor" / stroke="currentColor".
// Цвет управляется через text-* класс родителя.
<ChevronIcon className="text-app-muted h-4 w-4" />;
```

Inline SVG в JSX — **только** для one-off декоративных вещей. Для всего переиспользуемого — отдельный файл в `assets/icons/`.

## API-клиент паттерн

Client-side (`features/*/api/*.js`, `entities/*/api/*.js`):

```js
const res = await fetch('/api/something', { credentials: 'include' });
if (!res.ok) {
  const err = new Error('Понятное сообщение по-русски');
  err.status = res.status;
  throw err;
}
return res.json();
```

Server-side BFF (`app/api/*/route.js`):

```js
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

const token = await getAccessToken();
if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED', ... } }, { status: 401 });

const { ok, status, data } = await backendFetch('/api/v1/...', {
  headers: { Authorization: `Bearer ${token}` },
});
return NextResponse.json(data, { status: ok ? 200 : (status || 502) });
```

Error-envelope: `{ error: { code, message, details, request_id? } }`.

## Состояние

- Локальное → `useState`.
- Forms → `useReducer` (см. `useProductForm`).
- Кросс-страничный shared state → React Context (см. `AuthProvider`, `ToastProvider`, `PricingPageProvider`).
- Server cache → `getOrFetch()` из `@/shared/api/server-cache` (только в BFF-роутах).

Никакого Redux. Никакого Zustand/Jotai/MobX без согласования с командой.

## Обработка ошибок

- В UI всегда показать пользователю, что произошло. Не глотать молча.
- В catch — `setError(err.message ?? 'Понятное дефолтное сообщение')`.
- Для серверных 401 → клиент уже редиректит через middleware, дополнительно ничего не нужно.
- Для 429 — учитывать `retry-after` (см. `entities/product/api/products.js`).

## Комментарии

- Дефолт — **без комментариев**. Хорошие имена документируют сами себя.
- Пиши комментарий когда WHY неочевиден: обход бага, скрытое инвариант, нелогичный compromise.
- Не пиши «что» делает код — это видно. Пиши «почему».
- Никаких ссылок на task-id или PR-номера в коде.

## Что нельзя

- ❌ Cross-feature imports.
- ❌ Cross-entity deep imports.
- ❌ Прямой импорт `@/shared/mocks/*` из страниц/widgets — только через `entities/*`.
- ❌ `clsx()` напрямую — используй `cn()`.
- ❌ Hex-цвета в JSX `bg-[#xxx]` — используй `app-*` токены.
- ❌ Inline SVG в страницах для переиспользуемых иконок.
- ❌ Создавать новые директории `src/components/` / `src/hooks/` / `src/utils/` — это сломает FSD.
- ❌ `--no-verify` при коммите без явной причины и согласования.

## PR чеклист

Перед открытием PR:

- [ ] `npm run lint` — без ошибок
- [ ] `npm run build` — успешный production-build
- [ ] `npm run typecheck` — без ошибок
- [ ] `npm run format:check` — пройден
- [ ] Новые слайсы имеют `index.js` с public API
- [ ] Mock-only API помечен `*.mock.js` + TODO в barrel
- [ ] CHANGELOG обновлён (если есть user-facing изменения)
