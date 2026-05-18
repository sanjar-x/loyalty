# `src/widgets/` — Composite UI shells

Композитные UI-блоки страничной оболочки: header, footer, telegram-app-shell,
back-button, и **per-page композиции** (`HomePage`, `ProductPage`, ...).

В отличие от `features/` — почти не несут active actions, это **«UI-композиция»**:
собирают features + entities в готовый блок страницы.

## Структура — ПЛОСКАЯ (как в admin)

Без slice-структуры (`ui/model/api/lib/`) и **без `index.js`**.
Файлы лежат прямо в `src/widgets/`:

```
src/widgets/
├── Header.jsx
├── Footer.jsx
├── TelegramAppShell.jsx
├── HomePage/
│   ├── HomePage.jsx
│   ├── HomePage.module.css
│   └── (sub-components)
└── ProductPage/
    └── ...
```

Импорт по прямому пути: `import { Header } from '@/widgets/Header'`.

Если widget вырастает в полноценный slice (`ui/model/api/...`) — оформляй как
обычный slice в `features/`.

## Правила

- Может импортировать из: `features/`, `entities/`, `shared/`
- **Не может**: `app/`
- Cross-widget импорты — допустимы (sibling import не запрещён для widgets,
  потому что они плоские)
