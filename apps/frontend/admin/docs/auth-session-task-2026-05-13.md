# Auth Session Debugging Task — Admin Panel

**Дата:** 2026-05-13
**Компонент:** `frontend-admin`
**Симптом:** через несколько минут работы админ-панель просит пароль заново.
**Цель:** найти root cause, исправить, чтобы сессия держалась 30+ минут активной работы и нормально жила в нескольких вкладках.

---

## 1. Контекст — как работает auth (backend контракт)

### 1.1 Жизненный цикл токенов

```
POST /api/v1/auth/login   { login, password }
  → 200 { accessToken, refreshToken, tokenType: "bearer" }

accessToken  — JWT HS256, ttl = ACCESS_TOKEN_EXPIRE_MINUTES (15 мин)
refreshToken — opaque token (32 байта base64url), ttl = 30 дней
```

JWT payload содержит: `sub` (identity_id), `sid` (session_id), `tv` (token_version), `exp`, `iat`, `jti`.

### 1.2 Refresh — rotation, токен одноразовый

```
POST /api/v1/auth/refresh   { refreshToken }
  → 200 { accessToken, refreshToken }      ← новая пара, старый refresh инвалидирован
  → 401 SESSION_EXPIRED       (idle 30+ мин ИЛИ refresh старше 30 дней)
  → 401 SESSION_REVOKED       (был logout)
  → 401 REFRESH_TOKEN_REUSE   (старый refresh использован повторно → ВСЕ сессии identity отозваны)
```

**Критически важно:** backend хранит SHA-256 хеш текущего refresh token. При успешном refresh — хеш переписывается, старый токен становится «протухшим». Если кто-то предъявит старый хеш → reuse detected → backend **массово отзывает все активные сессии identity** (это защита от theft, см. `apps/backend/src/modules/identity/application/commands/refresh_token.py:155-198`). После reuse пользователю придётся логиниться заново на ВСЕХ устройствах/вкладках.

### 1.3 Session idle timeout — отдельный таймер от access TTL

`SESSION_IDLE_TIMEOUT_MINUTES = 30`. При каждом refresh у сессии в БД обновляется `idle_expires_at = now + 30m` (`Session.touch()`). Если 30 минут не было ни одного refresh — следующий refresh вернёт `SESSION_EXPIRED`.

Из этого следует: **если access expires каждые 15 мин и фронт делает refresh — сессия живёт до 30 дней. Если фронт молчит 30 мин — сессия умрёт.**

### 1.4 Ошибки от backend (envelope)

Backend всегда возвращает `{"error": {"code", "message", "details", "request_id"}}`. Релевантные codes:

| Code                    | HTTP | Что делать фронту                                       |
| ----------------------- | ---- | ------------------------------------------------------- |
| `TOKEN_EXPIRED`         | 401  | access истёк — попытаться refresh                       |
| `INVALID_TOKEN`         | 401  | access невалиден — logout, на /login                    |
| `MISSING_TOKEN`         | 401  | нет Bearer header — добавить или /login                 |
| `TOKEN_VERSION_STALE`   | 401  | сервер инвалидировал JWT (смена пароля и т.п.) — logout |
| `IDENTITY_INVALID`      | 401  | identity не найден или деактивирован — logout           |
| `SESSION_EXPIRED`       | 401  | refresh-ить нельзя — /login                             |
| `SESSION_REVOKED`       | 401  | logout сделан где-то ещё — /login                       |
| `REFRESH_TOKEN_REUSE`   | 401  | **серьёзно**, все сессии отозваны — /login + сообщение  |
| `INVALID_CREDENTIALS`   | 401  | неверный email/password при /login                      |
| `MAX_SESSIONS_EXCEEDED` | 429  | 5 активных сессий уже — нужен logout одной              |

---

## 2. Что уже реализовано (и работает корректно)

| Компонент       | Файл                                                      | Назначение                                                                                                 |
| --------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Edge proxy      | `apps/frontend/admin/src/proxy.js`                        | Перехватывает `/admin/:path*` и `/api/:path*`, при `expired access_token` → refresh → переписывает cookies |
| Cookie helpers  | `apps/frontend/admin/src/shared/auth/cookies.js`          | httpOnly + sameSite=lax, access maxAge=900s, refresh maxAge=2_592_000s                                     |
| BFF login       | `apps/frontend/admin/src/app/api/auth/login/route.js`     | Прокси к `/api/v1/auth/login`, ставит cookies                                                              |
| BFF refresh     | `apps/frontend/admin/src/app/api/auth/refresh/route.js`   | Прокси к `/api/v1/auth/refresh` (читает cookie, ставит новые)                                              |
| BFF me          | `apps/frontend/admin/src/app/api/auth/me/route.js`        | Декодирует JWT локально (без сетевого вызова)                                                              |
| AuthProvider    | `apps/frontend/admin/src/features/auth/model/useAuth.jsx` | React Context, при mount читает `/api/auth/me`                                                             |
| Dedup in-flight | `proxy.js:52-90`                                          | `inflight Map` с TTL 5s                                                                                    |

Архитектура **в целом верная**. Проблема — в деталях ниже.

---

## 3. Гипотезы root cause (расследовать ВСЕ)

### Гипотеза H1: дублирующий refresh-путь → REUSE → массовый logout (наиболее вероятная)

**Симптом:** «через несколько минут приходится вводить пароль каждый раз».

**Почему:** есть **два независимых пути refresh**, оба пишут в одни и те же cookies:

1. **Edge proxy** (`proxy.js`) — перехватывает любой `/api/*` или `/admin/*` запрос с истёкшим access_token.
2. **BFF route** `/api/auth/refresh` — в `AUTH_BYPASS_PATHS`, Edge proxy его НЕ перехватывает.

Если где-то на клиенте (или сторонняя библиотека-перехватчик типа TanStack Query / axios interceptor) явно POST'ит `/api/auth/refresh` параллельно с Edge proxy — оба прочитают **тот же** refresh_token из cookies, backend ротирует на первом, второй получит `REFRESH_TOKEN_REUSE` → **все сессии identity revoke**. Dedup `Map` в `proxy.js` это **не покрывает**, потому что BFF route handler — это Node runtime, а proxy — Edge runtime, у них разные процессы и разная in-memory память.

**Что проверить:**

- `grep -r "/api/auth/refresh" apps/frontend/admin/src` — найти все места, где код фронта явно вызывает refresh. Их быть **не должно**, refresh — внутреннее дело Edge proxy.
- Network tab браузера: при попадании на «требует пароль» посмотри какой запрос ПЕРВЫМ вернул 401. Если это `/api/auth/refresh` с body `REFRESH_TOKEN_REUSE` — гипотеза подтверждена.
- Логи backend (`apps/backend`): `refresh_token.reuse_confirmed` или `refresh_token.reuse_suspected` записи в момент логаута — прямое доказательство.

**Фикс:**

- Удалить любые клиентские вызовы `/api/auth/refresh` — пусть refresh делает **ТОЛЬКО** Edge proxy.
- BFF route `/api/auth/refresh/route.js` оставить как явный fallback (для отладки), но НЕ вызывать его из обычного UI flow.
- Если нужен «принудительный refresh» — пусть им владеет Edge proxy (запрос триггерит matcher → proxy сам решит).

### Гипотеза H2: параллельные вкладки/окна → один refresh_token читают одновременно

**Симптом:** «открыл вторую вкладку — обе вылетели».

**Почему:** dedup `inflight Map` в `proxy.js` живёт в памяти одного Edge instance. На production (Netlify/Vercel/serverless) запросы из двух вкладок могут попасть на разные instance'ы. Оба читают cookie с одним и тем же refresh_token, оба POST'ят backend, один выиграет, второй получит REUSE.

**Что проверить:**

- Закрой все вкладки кроме одной, оставь её на 20 минут, посмотри — выкидывает или нет.
- В DevTools → Application → Cookies, посмотри что refresh_token уникален для пользователя; при «вылете» проверь, рефрешится ли он.

**Фикс — на выбор (от простого к надёжному):**

1. **BroadcastChannel** между вкладками — одна «лидер» делает refresh, остальные ждут результат. Реализуется в `proxy.js` сложно (это Edge runtime, у него нет BC) — лучше на клиенте, в TanStack Query / fetch wrapper.
2. **Web Lock API** (`navigator.locks.request('auth-refresh', ...)`) — сериализует refresh между вкладками одного origin. Стандарт, работает в современных браузерах.
3. **Перенести refresh-логику в backend cookie-handler** — backend выпускает Set-Cookie на refresh и принимает `refreshToken` из httpOnly cookie напрямую. Но это меняет backend контракт, см. отдельную задачу.

### Гипотеза H3: idle timeout 30 мин при фоновом простое

**Симптом:** «оставил вкладку открытой на ночь, утром просит логин».

**Почему:** backend `SESSION_IDLE_TIMEOUT_MINUTES = 30`. Если фронт за 30 минут не сделал ни одного запроса (а значит ни одного refresh), сессия в БД помечается как idle-expired. Это **ожидаемое поведение** и менять его не надо — это security feature.

**Что проверить:**

- В Network tab при «вылете» сколько прошло между последним успешным запросом и попыткой пользоваться?

**Фикс:** документируй это для пользователей. Опционально: добавить heartbeat-запрос (пустой GET к `/api/auth/me` каждые 10 минут активной вкладки) — но это маскирует security feature. Лучше: показывать модалку «сессия истечёт через 2 минуты, продолжить?» за 2 минуты до idle expiry (на клиенте — таймер от последней user activity).

### Гипотеза H4: Edge proxy не срабатывает для определённого пути

**Симптом:** «работает на /admin/products, ломается на /admin/settings».

**Почему:** matcher `['/admin/:path*', '/api/:path*']` должен покрыть всё. Но Next.js 16 имеет нюансы с rewrites/route handlers — иногда static-генерация роутов обходит proxy.

**Что проверить:**

- Открой `/admin/orders` (или любой раздел где «вылетает») в новой вкладке с пустыми cookies — должен быть редирект на `/login`. Если редиректа НЕТ и страница рендерится с пустыми данными — proxy не сработал.
- Console.log в `proxy()` функции на каждый pathname — посмотри, ловит ли он то, что должен.

**Фикс:** убедись что `export const config.matcher` написан корректно, в Next.js 16 для проверки используй `NEXT_RUNTIME=edge npm run dev` и `console.log` в proxy.

### Гипотеза H5: cookie не sent на проблемном запросе

**Симптом:** «один конкретный fetch получает 401, остальные ок».

**Почему:** где-то fetch вызван без `credentials: 'include'`. По дефолту cookies НЕ отправляются на same-origin XHR в браузерах (зависит от настроек), для cross-origin — никогда без `include`.

**Что проверить:**

- В Network tab открой проблемный запрос → Request Headers — есть ли `Cookie: access_token=...`? Если нет — fetch некорректно сконфигурирован.
- `grep -rn "fetch(" apps/frontend/admin/src --include="*.js" --include="*.jsx" | grep -v "credentials"` — найти fetch'и без `credentials`.

**Фикс:** всегда использовать `apiClient` из `@/shared/api/client-fetch` (он ставит `credentials: 'include'`), либо явно прописывать в fetch.

### Гипотеза H6: SSR/RSC vs Client component — рассинхрон cookies

**Симптом:** «после login пустые данные на главной».

**Почему:** Server Component читает cookies на момент рендеринга. Если Edge proxy переписал cookies в ходе того же запроса, downstream Server Component МОЖЕТ видеть старые cookies (зависит от того, мутировался ли `request.cookies` в memory).

**Проверь:** в `proxy.js:154-155` уже стоит `request.cookies.set(...)` для in-flight mutation — это должно работать. Проверь в Next.js 16, что Server Component-ы читают `cookies()` после proxy.

---

## 4. Действия — что делать пошагово

### Шаг 1: диагностика (1-2 часа)

1. **Воспроизведи** проблему на dev. Открой DevTools → Network, фильтр XHR/Fetch, **сохрани HAR** в момент вылета.
2. **Найди первый 401** в HAR. Запиши:
   - URL запроса
   - `error.code` из response body
   - Cookies, отправленные в запросе (access_token и refresh_token присутствуют?)
3. **Проверь логи backend** (`apps/backend` — `docker logs` или Railway logs) на:
   - `refresh_token.reuse_confirmed` — гипотеза H1 подтверждена
   - `refresh_token.reuse_suspected` — почти то же самое, токен не нашёлся в БД
   - `session.refreshed` — refresh прошёл успешно (значит проблема не в refresh, а в чём-то ещё)
4. **Сравни** `iat` access token из последнего успешного запроса и время «вылета». Если разница ≥ 15 минут — access протух и refresh не сработал.

### Шаг 2: убрать дублирующий refresh-путь (если H1)

```bash
# Найти явные вызовы refresh
grep -rn "auth/refresh" apps/frontend/admin/src --include="*.js" --include="*.jsx"
```

Все вызовы НЕ из `proxy.js` — потенциальные источники race. Удалить или переписать так, чтобы пользоваться Edge proxy.

### Шаг 3: межвкладочная синхронизация (если H2)

В `src/shared/api/client-fetch.js` (или в новом `src/shared/auth/refresh-lock.js`) обернуть retry-on-401 логику в Web Lock:

```js
async function withRefreshLock(fn) {
  if (!navigator.locks) return fn(); // fallback для старых браузеров
  return navigator.locks.request(
    'admin-auth-refresh',
    { mode: 'exclusive' },
    fn,
  );
}
```

Но **первичный путь refresh должен оставаться Edge proxy**. Web Lock — это про координацию **retry на клиенте** после 401, чтобы вкладки не дёргали Edge proxy одновременно с одинаковыми протухшими cookies.

### Шаг 4: правильная обработка 401 на клиенте

В `client-fetch.js` уже бросается `ApiError` с `code/status`. Добавить в местах, где UI его ловит:

```js
catch (err) {
  if (err instanceof ApiError && err.status === 401) {
    if (err.code === 'REFRESH_TOKEN_REUSE') {
      toast.error('Безопасность: вход выполнен на другом устройстве. Войдите заново.');
    } else if (err.code === 'SESSION_EXPIRED') {
      toast.info('Сессия истекла после периода неактивности. Войдите снова.');
    }
    // НЕ дёргать /api/auth/refresh — это сделает Edge proxy на следующем запросе
    router.push('/login');
    return;
  }
  throw err;
}
```

**Никогда** на клиенте не вызывать `/api/auth/refresh` — пусть Edge proxy сам разберётся при следующем переходе.

### Шаг 5: подтвердить idle timeout (если H3)

Реализовать «soft warning» за 2 минуты до idle expiry:

```js
// useIdleTimer.js (упрощённо)
const IDLE_LIMIT_MS = 28 * 60_000; // 28 мин — на 2 мин раньше backend (30 мин)
const lastActivity = useRef(Date.now());
useEffect(() => {
  const onActivity = () => {
    lastActivity.current = Date.now();
  };
  ['mousemove', 'keydown', 'click'].forEach((e) =>
    window.addEventListener(e, onActivity),
  );
  const id = setInterval(() => {
    if (Date.now() - lastActivity.current > IDLE_LIMIT_MS) {
      showModal('Сессия истечёт через 2 минуты, продолжить?');
    }
  }, 30_000);
  return () => {
    clearInterval(id);
    ['mousemove', 'keydown', 'click'].forEach((e) =>
      window.removeEventListener(e, onActivity),
    );
  };
}, []);
```

При нажатии «Продолжить» — выполнить любой GET (например `/api/auth/me` или любой данный запрос), Edge proxy сделает refresh, сессия в БД тоже обновится.

### Шаг 6: добавить наблюдаемость

- В `proxy.js` добавить `console.log('[auth-proxy]', { pathname, refreshed: result.ok })` (в dev) или structured log в production.
- В `useAuth` логировать moment'ы `setUser(null)` с причиной (response code от `/api/auth/me`).
- На backend в `refresh_token.py` уже есть логи — попроси DevOps вывести их на дашборд.

---

## 5. Acceptance criteria

- [ ] Сессия в админ-панели держится минимум 30 минут активной работы без запроса пароля.
- [ ] При неактивности 30+ минут пользователь видит понятное сообщение «Сессия истекла, войдите снова», а не молчаливый редирект.
- [ ] Открытие 2-3 вкладок одной сессии **не вызывает** массового logout.
- [ ] В Network tab за 30 минут активной работы виден **строго 1 POST** на `/api/v1/auth/refresh` каждые ~15 минут (когда access протухает), от Edge proxy.
- [ ] В backend логах при нормальном использовании НЕТ записей `refresh_token.reuse_confirmed`.
- [ ] При REUSE (если случается) — toast объясняет пользователю причину, не просто кикает на login.

---

## 6. Контракт с backend (для справки разработчика)

Если в ходе расследования выяснится, что что-то нужно изменить на backend — НЕ менять без согласования. Backend контракт:

- **Login:** `POST /api/v1/auth/login` body `{login, password}` → 200 `{accessToken, refreshToken, tokenType}` либо 401 `{error: {code: "INVALID_CREDENTIALS", ...}}`.
- **Refresh:** `POST /api/v1/auth/refresh` body `{refreshToken}` → 200 `{accessToken, refreshToken, tokenType}` либо 401 `{error: {code: "SESSION_EXPIRED" | "SESSION_REVOKED" | "REFRESH_TOKEN_REUSE", ...}}`.
- **Logout:** `POST /api/v1/auth/logout` с `Authorization: Bearer <accessToken>` → 200 `{message}`. Отзывает только текущую сессию.
- **Logout all:** `POST /api/v1/auth/logout/all` → отзывает все сессии identity.
- Любой защищённый endpoint без валидного Bearer → 401 + один из `MISSING_TOKEN | TOKEN_EXPIRED | INVALID_TOKEN | TOKEN_VERSION_STALE | IDENTITY_INVALID`.

Поля ответа всегда **camelCase** (Pydantic `CamelModel`), не snake_case.

---

## 7. Подсказка по приоритетам

1. **Сначала** проверь Network tab + backend логи — это 30 минут и сразу скажет, какая гипотеза.
2. Если H1 (REUSE) — найти и удалить дублирующий refresh путь это 1-2 часа.
3. H2 (multi-tab) — Web Lock реализация ~3 часа с тестами.
4. H3 (idle) — это by design, объяснить пользователю, опционально soft warning ~2 часа.
5. H4-H6 — менее вероятны, проверить если основные не подошли.

После фикса прогнать smoke: login → подождать 20 мин с активностью → должно работать; открыть 3 вкладки → подождать 5 мин → все должны жить; logout в одной → остальные через ~15 мин должны выйти на /login с сообщением.

---

Если у тебя нет доступа к backend логам или нужны конкретные SQL запросы к `sessions`/`outbox_messages` для верификации reuse — попроси DevOps или меня. Готов парно дебажить если воспроизведёшь.
