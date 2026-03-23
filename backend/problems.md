# =====================================================================================

# DEEP CODE REVIEW: MODULE CATALOG

# 7 Parallel Opus 4.6 Agents | 2026-03-23

# =====================================================================================

# ╔═══════════════════════════════════════════════════════════════════════════════════════╗

# ║ MEDIUM — SHOULD FIX ║

# ╚═══════════════════════════════════════════════════════════════════════════════════════╝

# ── NAMING ────────────────────────────────────────────────────────────────────────────

# [MEDIUM] NAME-02: Delete vs Remove vs Unbind — несогласованность глаголов

# remove*product_attribute vs delete*\* для аналогичных операций.

# VariantRemovedEvent vs AttributeValueDeletedEvent.

# FIX: Стандартизировать: Delete для persistence ops, Remove для aggregate child ops.

# [MEDIUM] NAME-04: value_group (domain) vs group_code (ORM) — deliberate rename

# Файлы: entities.py:744, models.py:377

# FIX: Документировано, но создаёт cognitive overhead.

# ── SECURITY ──

# [MEDIUM] SEC-08: Нет rate limiting на генерацию presigned URLs

# Файл: presentation/router_product_media.py:53-80

# FIX: Rate limit middleware + проверка кол-ва PENDING_UPLOAD media.

# [MEDIUM] SEC-10: Public read endpoints без авторизации

# Admin list/get для categories, brands, attributes — без RequirePermission.

# FIX: Добавить catalog:read permission или документировать как intentional.

# ── QUALITY ────────────────────────────────────────────────────────────────────────────

# ╔═══════════════════════════════════════════════════════════════════════════════════════╗

# ║ MEDIUM — TO FIX ║

# ╚═══════════════════════════════════════════════════════════════════════════════════════╝

# [MEDIUM] MEDIA_ROLE_MAIN = "main" magic string, дублирует MediaRole.MAIN из infrastructure

# [MEDIUM] ProductStatus docstring ссылается на infrastructure/models.py

# [MEDIUM] Event **post_init** boilerplate повторён 22 раза

# [MEDIUM] \_limit_validation_rules_size validator дублирован в 2 schema

# [MEDIUM] Money VO construction boilerplate в 3 handlers

# [MEDIUM] get_for_update pattern дублирован в 3 repositories

# [MEDIUM] has_products existence check дублирован в brand/category repos

# [MEDIUM] Logger injection inconsistent — не все handlers имеют ILogger

# [MEDIUM] group_repo vs {entity}\_repo — naming inconsistency

# [MEDIUM] ProductAttributeValueReadModel near-duplicate of ProductAttributeReadModel

# [MEDIUM] confirm_brand_logo.py class includes "Upload", media doesn't

# [MEDIUM] \_to_product_response private vs to_sku_response public in mappers

# [MEDIUM] Magic number 300 для presigned URL expiration

# [MEDIUM] build_update_command возвращает Any — lost type safety

# [MEDIUM] search_aliases без size limits

# [MEDIUM] Inconsistent ILIKE escaping (\% vs \\%)

# [MEDIUM] i18n dict keys не валидируются (любой string как language code)

# [MEDIUM] Cache poisoning via stale storefront cache (attribute removals)

# [MEDIUM] Fragile coupling: raw SQL index condition vs Python enum
