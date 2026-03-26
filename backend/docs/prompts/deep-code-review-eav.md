# DEEP Code Review: EAV-система каталога

> **Формат:** Ты — внешний Senior Code Reviewer. Тебя наняли для глубокого ревью attribute-подсистемы перед production launch.
> **Ожидание:** Ищи баги, race conditions, data corruption risks, security holes, performance bottlenecks, inconsistencies. Не хвали — только проблемы.
> **Severity:** P0 = блокер релиза, P1 = серьёзная проблема, P2 = должно быть исправлено, P3 = tech debt
> **Правило:** Каждая находка = конкретный файл:строка + воспроизводимый сценарий + предложенный fix

---

## Что ревьюить

Прочитай КАЖДЫЙ файл из этого списка. Не пропускай. Не скимай.

### Domain Layer

```
src/modules/catalog/domain/entities.py          — ВСЕ entity классы (~2000 строк)
src/modules/catalog/domain/value_objects.py      — BehaviorFlags, enums, Money
src/modules/catalog/domain/interfaces.py         — ВСЕ repository interfaces
src/modules/catalog/domain/exceptions.py         — exception hierarchy
src/modules/catalog/domain/events.py             — domain events
```

### Infrastructure Layer

```
src/modules/catalog/infrastructure/models.py     — ВСЕ ORM models (~870 строк)
src/modules/catalog/infrastructure/repositories/  — ВСЕ файлы в директории
src/modules/catalog/infrastructure/image_backend_client.py  — если есть
```

### Application Layer

```
src/modules/catalog/application/commands/         — ВСЕ command handlers
src/modules/catalog/application/queries/          — ВСЕ query handlers
src/modules/catalog/application/constants.py      — cache keys, TTL
```

### Presentation Layer

```
src/modules/catalog/presentation/schemas.py       — ВСЕ Pydantic schemas
src/modules/catalog/presentation/router_*.py      — ВСЕ routers
src/modules/catalog/presentation/dependencies.py  — DI wiring
```

### Tests

```
tests/integration/modules/catalog/               — ВСЕ test файлы
tests/unit/modules/catalog/                       — ВСЕ test файлы
```

---

## Что искать (checklist)

### 1. Correctness — баги и data corruption

- [ ] **Off-by-one / boundary conditions:** пустые списки, None checks, empty dicts
- [ ] **Race conditions:** два запроса одновременно создают/удаляют один ресурс. `check_exists()` → `create()` gap (TOCTOU)
- [ ] **Partial failure:** что если commit прошёл, но cache invalidation упала? Stale cache навсегда?
- [ ] **FK integrity:** можно ли удалить entity, на который ссылается другой? Cascade rules правильные?
- [ ] **Optimistic locking:** `version` column на Product/SKU — правильно ли инкрементируется? Что если 2 PM редактируют одновременно?
- [ ] **Soft-delete consistency:** `deleted_at` на Product/SKU — все queries фильтруют? Не leaks ли deleted product в storefront?
- [ ] **effective_template_id propagation:** что если parent category удалена? Child's effective_template_id stale?
- [ ] **Domain invariants:** может ли entity оказаться в невалидном состоянии? (negative sort_order, empty name_i18n, etc.)

### 2. Security

- [ ] **SQL injection:** raw SQL через `text()` — параметры правильно bind-ятся?
- [ ] **Permission bypass:** storefront endpoints public, admin endpoints require `catalog:manage`. Нет ли admin-only данных в public responses?
- [ ] **Mass assignment:** Pydantic schemas — какие поля принимает PATCH? Может ли PM обновить `id`, `created_at`, `version`?
- [ ] **IDOR:** может ли user A видеть/менять products user B? (pre-multi-tenant, но всё равно проверить)
- [ ] **Input validation:** max lengths enforced? JSONB size limited? Array lengths bounded?

### 3. Performance

- [ ] **N+1 queries:** for-loop с `await repo.get()` внутри. Уже фиксили bulk_assign — проверь что нигде больше нет.
- [ ] **Missing indexes:** queries в handlers, которые не покрыты indexes в models.py
- [ ] **Unbounded queries:** `SELECT *` без LIMIT. List endpoints с `limit=10000`?
- [ ] **Cache key collisions:** разные entities с одинаковым UUID генерируют одинаковый cache key?
- [ ] **Memory leaks:** загрузка всех products/values в память без pagination
- [ ] **Slow queries:** JOINs через 4+ таблиц, subqueries в WHERE

### 4. CQRS / DDD Compliance

- [ ] **Infrastructure leak:** domain/application layer импортирует ORM models? (`from ...infrastructure.models import`)
- [ ] **Anemic entities:** domain entity без бизнес-логики (только data fields)?
- [ ] **Fat handlers:** handler >100 строк с бизнес-логикой которая должна быть в domain?
- [ ] **Command returns data:** command handler возвращает read model? (CQRS violation — command should return minimal result)
- [ ] **Query mutates state:** query handler делает write? cache set допустим, но DB write — нет

### 5. Error Handling

- [ ] **Swallowed exceptions:** `except Exception: pass` или `except Exception as e: log.warning()`
- [ ] **Wrong HTTP status:** exception → 500 вместо 400/404/409?
- [ ] **Leaking internals:** error messages expose SQL, table names, internal UUIDs?
- [ ] **Missing error paths:** что если FK target не существует? Graceful error или IntegrityError?

### 6. Data Model

- [ ] **Missing constraints:** бизнес-правило в коде, но не в DB? (пример: "code immutable" — enforced только в entity, не в DB trigger)
- [ ] **Wrong cascade:** `ondelete="CASCADE"` где должен быть `"RESTRICT"`? Или наоборот?
- [ ] **JSONB without bounds:** JSONB columns без CHECK constraint на size? Кто-то может POST 10MB JSON?
- [ ] **Enum drift:** Python enum и PG enum out of sync? Новое значение в Python, но ALTER TYPE не сделан?

### 7. Concurrency & Transactions

- [ ] **Transaction scope:** handler открывает `async with self._uow` но делает work ПОСЛЕ commit?
- [ ] **Session reuse:** два handlers в одном request шарят session? Dirty reads?
- [ ] **Deadlocks:** два handlers лочат rows в разном порядке?
- [ ] **Cache-DB inconsistency:** cache invalidated BEFORE commit? (should be AFTER)

### 8. Testing Gaps

- [ ] **Untested happy paths:** handler без единого теста
- [ ] **Untested edge cases:** empty list, None, max-length string, concurrent modification
- [ ] **Untested error paths:** что если repo.get() returns None? Тест есть?
- [ ] **Flaky tests:** tests зависят от порядка, от global state, от timing

---

## Формат находки

```markdown
### [P0/P1/P2/P3] [Категория]: Заголовок

**Файл:** `path/to/file.py:line`
**Код:**
```python
# exact code snippet
```

**Проблема:** 2-3 предложения — что не так и почему это опасно.

**Сценарий воспроизведения:**
1. Step 1
2. Step 2
3. Наблюдаемый результат vs ожидаемый

**Предложенный fix:**
```python
# corrected code
```

**Impact:** что сломается если не починить (data corruption / stale cache / security hole / etc.)
```

---

## Формат итога

### Summary Table

```
| #   | Sev | Category    | File:Line               | Title                           |
| --- | --- | ----------- | ----------------------- | ------------------------------- |
| 1   | P0  | Correctness | entities.py:123         | Race condition in ...           |
| 2   | P1  | Security    | router_attributes.py:45 | Missing permission check on ... |
| ... |
```

### Scorecard

```
| Category           | Score (1-10) | Critical Issues |
| ------------------ | :----------: | :-------------: |
| Correctness        |      ?       |        ?        |
| Security           |      ?       |        ?        |
| Performance        |      ?       |        ?        |
| Architecture (DDD) |      ?       |        ?        |
| Error Handling     |      ?       |        ?        |
| Data Model         |      ?       |        ?        |
| Concurrency        |      ?       |        ?        |
| Test Coverage      |      ?       |        ?        |
| Overall            |      ?       |        ?        |
```

### Verdict

```
[ ] READY for production
[ ] READY with conditions (list blockers)
[ ] NOT READY (list P0 blockers)
```

---

## Что НЕ делать

- **Не хвали.** Если код хороший — не упоминай. Ищи только проблемы.
- **Не предлагай рефакторинг** "было бы красивее если...". Только реальные проблемы.
- **Не повторяй** известные issues (effective_family_id bug — уже пофикшен, exclusions — уже удалены).
- **Не ревьюй docs/, prompts/, reviews/** — только .py файлы.
- **Не ревьюй** другие модули (identity, user, supplier, geo) — только catalog.

Сохрани результат в `backend/docs/reviews/deep-code-review-eav.md`
