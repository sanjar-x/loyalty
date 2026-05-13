# PR Reconciliation — 2026-05-10

Контекст: hotfix-спринт между Sprint 3 и Sprint 4. На момент LOG-003
hotfix-ветки в репозитории были два открытых PR от предыдущих сессий
BE-2 (06.05). Оба провисели > 3 дней, за это время main ушёл вперёд на
22 коммита (Sprint 1+2+3 + смок-результаты + close-tracker). Эта
заметка фиксирует решение по каждому, чтобы при последующем `gh pr close`
было читаемое обоснование.

## PR #29 — REC-024 GHA cleanup

- Title: `chore(ci): remove inactive GHA workflow + align verification docs (REC-024)`
- Branch: `chore/REC-024-remove-inactive-gha-workflow`
- HEAD коммит: `599215c3`
- Decision: **closed-as-superseded**
- Reason:

  Изменение, которое предлагал PR #29, **уже в main** — коммит
  [`f78a6e1a chore(ci): remove inactive GHA workflow + align verification docs (REC-024) (#28)`](
  https://github.com/sanjar-x/loyalty/commit/f78a6e1a). PR #28 (smaller
  squash от того же diff) был мерджен ранее, а PR #29 остался открытым
  как дубль.

  Verification:
  - `find .github/workflows -type f` ⇒ директория не существует на
    main HEAD.
  - `backend/CLAUDE.md` уже содержит «CI Verification Matrix» с four-
    layer стэком (REC-019 pre-push, Railway preDeploy, CodeRabbit, TL
    review).
  - `git log origin/main --oneline | grep REC-024` ⇒ один коммит
    `f78a6e1a` (squash от #28).

  Branch PR #29 ушёл от main — `git diff origin/main pr-29 --stat`
  показывает 25+ файлов с deletions (новые миграции, sprint-3 docs,
  etc.) которые были добавлены в main после создания этой ветки.
  Merge сейчас откатит свежие изменения. Rebase ради дубля
  бессмысленен — нужного effect'а уже добился #28.

- Action: `gh pr close 29 --comment "Superseded by #28 (commit f78a6e1a). The same diff was merged via the squash PR #28; this branch has since diverged from main and would now revert unrelated subsequent commits if rebased. No further action required — REC-024 is complete on main."`

## PR #30 — HARD-2 Telegram alerter

- Title: `feat(alerts): Telegram alerter + outbox/DLQ monitors (HARD-2)`
- Branch: `feat/HARD-2-telegram-alerter-monitors`
- Decision: **closed-as-superseded-by-D2.1+D2.2**
- Reason:

  Sprint 3 D2.1 (OBS-001) + D2.2 (OBS-002), смерджены в main коммитом
  [`bc491d87 feat(observability): outbox lag metric + DLQ growth alerting (OBS-001 / OBS-002)`](
  https://github.com/sanjar-x/loyalty/commit/bc491d87), уже закрывают
  исходную HARD-2 цель — операционный мониторинг outbox lag и DLQ
  growth. Реализация:

  | Aspect | PR #30 (proposed) | D2.1 + D2.2 (in main) |
  | --- | --- | --- |
  | Outbox lag check | every minute, CRITICAL > 50 pending OR > 5 min | every minute, INFO/WARN при > 5 min lag |
  | DLQ growth check | every minute, WARNING на каждое новое failed_tasks | every 15 min, ERROR при > 10 fails/15min |
  | Channel | Telegram Bot API (`TG_ALERTS_CHANNEL`) | structured logs (JSON) |
  | Tests | 17 unit (TelegramAlerter, AlertLevel, monitors) | проверяется через log assert + sprint smoke |

  Содержательные различия — это **complement**, не **overlap**:
  D2.x пушит в structured logs (видно в `kubectl logs` / Railway logs /
  лог-агрегаторе); PR #30 пушит в Telegram канал. Но запускать оба
  одновременно сейчас нецелесообразно по двум причинам:

  1. **Threshold mismatch**. D2.2 фильтрует `> 10 fails / 15min`
     (предполагая «один транзиентный фейл — не повод будить on-call»);
     PR #30 алёртит на каждое новое fails в минутном окне (per-process
     watermark). Без согласования thresholds получаем noisy duplicate.

  2. **Branch outdated**. PR #30 был открыт 06.05 на пост-REC-024
     HEAD'е (`f78a6e1a`), с тех пор в main вошли OBS-001/OBS-002
     (bc491d87), PII redaction (12d6b732), recipient-status fix
     (484f5136), async DobroPost booking (9fed188b), sprint-3 close
     (0ee006c3), LOG-003 hotfix (текущий PR). Re-base потребует
     non-trivial conflict resolution на `src/bootstrap/config.py`,
     `src/bootstrap/scheduler.py`, `src/bootstrap/worker.py` и
     `backend/CLAUDE.md` — usually overlap-region.

  Sprint 4 backlog уже содержит item для **Telegram bot push consumer
  for shipment events (D3.1 deferred)**. Когда придёт время, чище
  добавить Telegram push прямо в существующие D2.1/D2.2 task body
  (один-два `await alerter.send(...)` вызова), чем re-base'ить весь
  PR #30.

- Action: `gh pr close 30 --comment "Superseded by D2.1 (commit bc491d87) + D2.2 — outbox lag and DLQ growth alerting now ship as structured-log monitors (OBS-001 / OBS-002) in main. Branch has since diverged on src/bootstrap/{config,scheduler,worker}.py and backend/CLAUDE.md. Telegram push is deferred to Sprint 4 backlog (D3.1) — when picked up, cleaner to add an alerter.send(...) call inside the existing _outbox_lag_metric_task / failed_tasks_alert_task than to rebase this branch."`

## Summary

| PR | Decision | Action |
| --- | --- | --- |
| #29 | closed-as-superseded | `gh pr close 29 ...` |
| #30 | closed-as-superseded-by-D2.x | `gh pr close 30 ...` |

Backlog impact:
- Sprint 4 picks up Telegram alerter as a small PR on top of D2.1/D2.2
  (D3.1 deferred from Sprint 3).
- No tickets re-opened — REC-024 closed on main; HARD-2 partially
  achieved via OBS-001/OBS-002, residual «push to Telegram» moves to
  D3.1 in Sprint 4.
