# Каталог атрибутов качества ПО

> Источники: ISO 25010:2023 (SQuaRE), ISO 25012 (Data Quality), OWASP, 12-Factor App, Clean Architecture, SRE Book, практика e-commerce.

---

## 1. Functional correctness

| #   | Качество                   | Определение                                             |
| --- | -------------------------- | ------------------------------------------------------- |
| 1   | **Correctness**            | Результаты соответствуют спецификации                   |
| 2   | **Completeness**           | Все требования реализованы                              |
| 3   | **Accuracy**               | Вычисления и данные точны                               |
| 4   | **Appropriateness**        | Функции решают реальную задачу пользователя             |
| 104 | **Behavioral determinism** | Одинаковый input → одинаковый output (без hidden state) |

## 2. Reliability & fault tolerance

| #   | Качество                  | Определение                                             |
| --- | ------------------------- | ------------------------------------------------------- |
| 5   | **Availability**          | Доступен когда нужен                                    |
| 6   | **Recoverability**        | Восстанавливается после полного сбоя                    |
| 7   | **Resilience**            | Устойчив к сбоям, перегрузкам и непредвиденным условиям |
| 105 | **Backpressure handling** | Контролирует входящий поток при перегрузке              |
| 106 | **Timeout management**    | Все внешние вызовы имеют timeout                        |
| 108 | **Graceful shutdown**     | При остановке — дообрабатывает in-flight запросы        |

## 3. Data integrity & concurrency (ACID / CRDTs)

| #   | Качество                    | Определение                                               |
| --- | --------------------------- | --------------------------------------------------------- |
| 8   | **Data integrity**          | Данные не повреждаются: FK, PK/UNIQUE, domain constraints |
| 9   | **Data consistency**        | Данные согласованы между PG, Redis, ES                    |
| 10  | **Idempotency**             | Повторный вызов API даёт тот же результат (safe retry)    |
| 11  | **Durability**              | Committed данные не теряются при crash                    |
| 12  | **Race condition freedom**  | Параллельные запросы не приводят к data corruption        |
| 13  | **Deadlock freedom**        | Нет взаимных блокировок                                   |
| 14  | **Optimistic concurrency**  | Конфликтующие UPDATE обнаруживаются (version/etag)        |
| 15  | **Multi-tenancy isolation** | Данные и нагрузка одного tenant не влияют на другого      |

## 4. Performance & efficiency (USE method)

| #   | Качество                | Определение                                    |
| --- | ----------------------- | ---------------------------------------------- |
| 16  | **Latency**             | Время ответа API                               |
| 17  | **Throughput**          | Количество запросов в секунду                  |
| 18  | **Scalability**         | Способность расти под нагрузкой без деградации |
| 19  | **Elasticity**          | Автоматическое масштабирование вверх/вниз      |
| 20  | **Capacity**            | Максимум данных/users до деградации            |
| 21  | **Resource efficiency** | CPU/RAM/disk/cost per operation                |
| 22  | **Cache effectiveness** | Cache hit rate, invalidation correctness       |
| 23  | **Query efficiency**    | SQL round-trips per user action                |
| 24  | **Payload efficiency**  | Размер API response                            |
| 25  | **Cold start**          | Время до первого ответа после deploy           |
| 107 | **Connection pooling**  | Переиспользование DB/HTTP/Redis connections    |

## 5. Security (OWASP / Zero Trust)

| #   | Качество                         | Определение                                        |
| --- | -------------------------------- | -------------------------------------------------- |
| 26  | **Confidentiality**              | Данные доступны только авторизованным              |
| 27  | **Authentication**               | Достоверная проверка личности                      |
| 28  | **Authorization**                | Правильный контроль доступа к ресурсам             |
| 29  | **Input validation**             | Защита от injection, XSS, overflow                 |
| 30  | **Output encoding**              | Ответы не содержат executable content              |
| 31  | **Secrets management**           | Пароли, ключи, токены не в коде и не в логах       |
| 32  | **Encryption**                   | Данные зашифрованы при хранении и передаче         |
| 33  | **Auditability**                 | Все мутации логируются (кто, когда, что)           |
| 34  | **Non-repudiation**              | Действие нельзя отрицать                           |
| 35  | **Attack surface**               | Минимум точек входа для атаки                      |
| 36  | **Dependency security**          | Зависимости без known CVE                          |
| 37  | **Rate limiting**                | Защита от brute-force и DDoS                       |
| 38  | **Supply chain security (SBOM)** | Знание полного дерева зависимостей и их provenance |

## 6. Usability & accessibility

| #   | Качество                 | Определение                                          |
| --- | ------------------------ | ---------------------------------------------------- |
| 39  | **Learnability**         | Как быстро новый PM начинает продуктивно работать    |
| 40  | **Error recovery**       | Понятные ошибки, возможность исправить без developer |
| 41  | **Accessibility**        | Доступен для людей с ограничениями (WCAG 2.1)        |
| 42  | **Internationalization** | Поддержка нескольких языков (ISO 639, ICU, CLDR)     |
| 43  | **Responsiveness**       | UI адаптивен на mobile/tablet/desktop                |

## 7. Interoperability & compatibility

| #   | Качество                      | Определение                                               |
| --- | ----------------------------- | --------------------------------------------------------- |
| 44  | **System interoperability**   | Обмен данными с внешними системами                        |
| 45  | **Protocol compatibility**    | Поддержка стандартных протоколов (OAuth2, OpenID Connect) |
| 46  | **Data format compatibility** | Import/export в стандартных форматах (CSV, XML, JSON-LD)  |
| 47  | **Co-existence**              | Работает с другими системами, не конфликтуя за ресурсы    |

## 8. SOLID & Clean Architecture

| #   | Качество                  | Определение                                           |
| --- | ------------------------- | ----------------------------------------------------- |
| 50  | **Loose coupling**        | Компоненты минимально зависят друг от друга           |
| 51  | **Single responsibility** | Каждый класс/модуль/слой — одна причина для изменения |
| 52  | **Open-closed**           | Расширение без модификации                            |
| 53  | **Interface segregation** | Узкие интерфейсы вместо толстых (нет unused methods)  |
| 54  | **Dependency inversion**  | Зависимости на абстракциях, направлены внутрь         |
| 61  | **Encapsulation**         | Внутренности скрыты за публичным интерфейсом          |

## 9. Maintainability & code health

| #   | Качество                   | Определение                                                 |
| --- | -------------------------- | ----------------------------------------------------------- |
| 48  | **Readability**            | Код понятен при первом чтении (naming, comments, structure) |
| 49  | **Cognitive complexity**   | Количество ментальных переключений при чтении функции       |
| 55  | **Event-driven readiness** | Система готова к async event processing                     |
| 56  | **Composability**          | Модули можно комбинировать в новые workflows                |
| 57  | **Modifiability**          | Легко внести типичное изменение                             |
| 58  | **Stability**              | Изменение одного модуля не ломает другой                    |
| 59  | **Modularity**             | Компоненты можно развивать независимо                       |
| 60  | **DRY**                    | Нет дублирования бизнес-логики                              |
| 62  | **Consistency**            | Одинаковые паттерны для одинаковых задач (код, API, UI)     |
| 63  | **Discoverability**        | Нужный код можно найти по naming и структуре                |
| 75  | **Brevity**                | Минимум кода для выражения идеи без потери ясности          |
| 76  | **Absence of waste**       | Нет мёртвого кода, unused imports, лишних абстракций        |
| 66  | **Technical debt ratio**   | Доля кода, который "нужно переписать"                       |

## 10. Configuration (12-Factor)

| #   | Качество                          | Определение                                 |
| --- | --------------------------------- | ------------------------------------------- |
| 64  | **Configuration externalization** | Настройки вне кода (env vars, config files) |
| 65  | **Configuration validation**      | Невалидный config = fast fail при старте    |
| 101 | **Environment parity**            | dev/staging/prod идентичны                  |

## 11. Testing (Test Pyramid)

| #   | Качество                | Определение                                           |
| --- | ----------------------- | ----------------------------------------------------- |
| 67  | **Testability**         | Код можно покрыть тестами без heroics                 |
| 68  | **Test coverage**       | % кода, покрытого тестами                             |
| 69  | **Test isolation**      | Каждый тест независим — порядок не имеет значения     |
| 70  | **Test determinism**    | Тесты дают одинаковый результат каждый раз            |
| 71  | **Mockability**         | Зависимости легко подменить через DI/interfaces       |
| 72  | **Test speed**          | Тесты выполняются быстро (fast feedback loop)         |
| 73  | **Test readability**    | Тесты читаются как спецификация (Arrange-Act-Assert)  |
| 74  | **Mutation test score** | Тесты ловят реальные баги, не просто покрывают строки |

## 12. Data quality (ISO 25012)

| #   | Качество                           | Определение                                   |
| --- | ---------------------------------- | --------------------------------------------- |
| 77  | **Data completeness**              | Required поля заполнены                       |
| 78  | **Data uniqueness**                | Нет нежелательных дубликатов                  |
| 79  | **Data timeliness**                | Данные актуальны (cache freshness, sync lag)  |
| 80  | **Data traceability**              | Происхождение и изменения прослеживаются      |
| 81  | **Schema & data migration safety** | DB-схему и данные можно безопасно мигрировать |

## 13. API design (REST / contract)

| #   | Качество                        | Определение                                               |
| --- | ------------------------------- | --------------------------------------------------------- |
| 82  | **Forward compatibility**       | Старый consumer понимает данные от нового producer        |
| 83  | **Error clarity**               | Ошибки понятны и actionable для consumer                  |
| 84  | **Pagination consistency**      | Единый формат пагинации                                   |
| 85  | **Schema completeness**         | Все поля задокументированы с типами и примерами           |
| 86  | **Backward compatibility**      | Новые версии не ломают существующих клиентов              |
| 87  | **API rate limit transparency** | Consumer знает свои лимиты через headers (X-RateLimit)    |
| 88  | **HTTP semantics**              | Правильные методы (GET, POST, PATCH)                      |
| 89  | **Status code correctness**     | HTTP статусы используются правильно                       |
| 90  | **Cache headers**               | ETag, Cache-Control, Last-Modified на cacheable endpoints |

## 14. Deployability & CI/CD

| #   | Качество                  | Определение                                   |
| --- | ------------------------- | --------------------------------------------- |
| 92  | **Rollbackability**       | Можно откатить деплой быстро без data loss    |
| 93  | **Zero-downtime deploy**  | Деплой без прерывания сервиса                 |
| 103 | **Build reproducibility** | Один и тот же commit даёт идентичный артефакт |

## 15. Observability (SRE Golden Signals)

| #   | Качество               | Определение                                               |
| --- | ---------------------- | --------------------------------------------------------- |
| 94  | **Structured logging** | Логи в JSON с correlation_id, user_id, request_id         |
| 95  | **Metrics collection** | RED metrics (Rate, Errors, Duration) per endpoint         |
| 96  | **Alerting**           | Автоматические alerts на аномалии (errors, latency, cost) |
| 97  | **Health checks**      | Readiness + liveness probes для orchestrator              |
| 98  | **Debuggability**      | Легко найти причину бага в dev и production               |

## 16. Developer experience (DX)

| #   | Качество                 | Определение                                             |
| --- | ------------------------ | ------------------------------------------------------- |
| 102 | **Installability**       | Новый разработчик запускает проект за <30 мин           |
| 109 | **Local dev cycle time** | Время от изменения кода до проверки результата          |
| 110 | **Tooling quality**      | Линтеры, форматтеры, генераторы — работают без friction |
| 111 | **Error DX**             | Ошибки при разработке понятны и actionable              |
| 112 | **Self-service**         | Разработчик может создать endpoint без помощи другого   |

## 17. Documentation

| #   | Качество                       | Определение                                |
| --- | ------------------------------ | ------------------------------------------ |
| 113 | **Architecture documentation** | ADRs, diagrams, module overview актуальны  |
| 114 | **Runbook coverage**           | Процедуры для инцидентов задокументированы |
| 115 | **Inline documentation**       | Docstrings на public interfaces            |

## 18. Compliance (GDPR / PCI DSS)

| #   | Качество            | Определение                                  |
| --- | ------------------- | -------------------------------------------- |
| 116 | **GDPR compliance** | Персональные данные обрабатываются по закону |
| 117 | **PCI DSS**         | Платёжные данные защищены (если applicable)  |
