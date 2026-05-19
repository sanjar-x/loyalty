## Что сделано

<!-- Кратко: 1-3 буллета о сути изменений. Что именно изменилось и почему. -->

-

## Тип изменения

- [ ] feat — новая функциональность
- [ ] fix — исправление бага
- [ ] refactor — рефакторинг без изменения поведения
- [ ] perf — оптимизация
- [ ] docs — только документация
- [ ] test — добавление/исправление тестов
- [ ] build / ci / chore

## Связанные задачи

<!-- Closes #123, Refs #456 -->

## Чеклист

### Качество кода

- [ ] `npm run lint` — 0 errors
- [ ] `npm run typecheck` — 0 errors
- [ ] `npm test` — все зелёные
- [ ] `npm run build` — успешный production-build
- [ ] `npm run format:check` — пройден
- [ ] Conventional Commit message в каждом коммите (`feat:`, `fix:`, …)

### FSD

- [ ] Новые слайсы (`features/*`, `entities/*`) экспортируют через `index.js`
- [ ] Нет cross-feature / cross-entity deep imports
- [ ] Mock-only API помечен `*.mock.js` + TODO в barrel
- [ ] Server-only код в `entities/category/server.js` (или аналог)

### UI

- [ ] Использован `cn()` из `@/shared/lib/utils`, не `clsx()` напрямую
- [ ] Цвета через дизайн-токены `app-*` (без `bg-[#xxx]`)
- [ ] SVG-иконки вынесены в `assets/icons/` (без inline `<svg>` в pages)
- [ ] i18n-объекты строятся через `buildI18nPayload(ru, en)`
- [ ] Все даты — `dayjs` из `@/shared/lib/dayjs`

### BFF и безопасность

- [ ] BFF-роуты используют `getAccessToken()` + `backendFetch()`
- [ ] Error-envelope `{ error: { code, message, details } }`
- [ ] Никаких секретов в коде / `.env.local` не в git

## Скриншоты / GIF

<!-- Для UI-изменений — до/после или короткий GIF -->

## Доп. контекст

<!-- Что-то, что важно знать ревьюеру: trade-offs, future work, известные ограничения -->
