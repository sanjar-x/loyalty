-- =============================================================================
-- seed_dev.sql — Dev database seed script
-- =============================================================================
-- Idempotent: safe to run multiple times (DELETE + INSERT for IAM,
-- ON CONFLICT DO NOTHING for catalog data).
--
-- Usage:
--   docker exec -i postgres psql -U postgres -d postgres < scripts/seed_dev.sql
--
-- Sections:
--   A. Permissions (13) — aligned with actual code enforcement
--   B. System roles (6)
--   C. Role-permission assignments
--   D. Role hierarchy
--   E. Dev admin user
--   F. Catalog data (brands + categories from categories.json)
-- =============================================================================

BEGIN;

-- =============================================================================
-- A. PERMISSIONS (13 total)
-- =============================================================================
-- Aligned with ACTUAL RequirePermission() checks in router code.
-- Format: resource:action
--   :read     — view data (GET)
--   :manage   — full CRUD (POST/PATCH/PUT/DELETE)
--   :update   — modify existing (PATCH)
--   :delete   — remove (DELETE)
--   :moderate — review/approve/reject content
--
-- UUIDs: uuid5(NAMESPACE_DNS, "perm.<codename>")
-- =============================================================================

-- Clean slate (dependency order: children first)
DELETE FROM role_hierarchy;
DELETE FROM role_permissions;
DELETE FROM identity_roles;
DELETE FROM roles;
DELETE FROM permissions;

INSERT INTO permissions (id, codename, resource, action, description) VALUES
  -- Catalog (brands, categories, products, attributes, SKUs)
  ('0123cb88-a31d-5e5a-88fc-2b18c896f01d', 'catalog:read',       'catalog',    'read',     'Просмотр каталога'),
  ('125a6f40-d2ff-5511-a5cb-deb9d2dc6907', 'catalog:manage',     'catalog',    'manage',   'Управление каталогом (бренды, категории, товары, атрибуты, SKU)'),
  -- Orders
  ('ad342625-eac5-591f-bddb-f86ab35d8c63', 'orders:read',        'orders',     'read',     'Просмотр заказов'),
  ('e72eae9b-68c9-51d3-b41f-62924ed1df0e', 'orders:manage',      'orders',     'manage',   'Управление заказами (создание, статусы, отмена, возвраты)'),
  -- Reviews
  ('7eefa86f-4c88-57ec-aa01-197b4173decf', 'reviews:read',       'reviews',    'read',     'Просмотр отзывов'),
  ('e52c8926-4eaa-56c6-839d-9b8de565d955', 'reviews:moderate',   'reviews',    'moderate', 'Модерация отзывов (одобрение, отклонение, удаление)'),
  -- Returns
  ('260ef83b-06b3-5e31-b60f-07dbd0666711', 'returns:read',       'returns',    'read',     'Просмотр возвратов'),
  ('7501bd14-845d-51de-a70c-335eb179ecdb', 'returns:manage',     'returns',    'manage',   'Обработка возвратов'),
  -- Users (self-service profile)
  ('12833502-d3f2-5eba-83ae-95a40cd06153', 'users:read',         'users',      'read',     'Просмотр профиля'),
  ('4acf2608-e539-5057-9373-8c935b18aeaf', 'users:update',       'users',      'update',   'Редактирование профиля'),
  ('8eadaeaf-ba4a-5747-b1f2-b360df386bca', 'users:delete',       'users',      'delete',   'Удаление аккаунта (GDPR)'),
  -- Admin IAM
  ('4236b6ca-8b53-5b65-9a66-b492351a07c1', 'roles:manage',       'roles',      'manage',   'Управление ролями и правами'),
  ('ab498b82-5aa9-5732-b724-4b1caf68b539', 'identities:manage',  'identities', 'manage',   'Управление пользователями (список, деактивация, роли)'),
  -- Staff management
  ('b1000000-0000-0000-0000-000000000001', 'staff:manage',        'staff',      'manage',   'Управление сотрудниками'),
  ('b1000000-0000-0000-0000-000000000002', 'staff:invite',        'staff',      'invite',   'Приглашение сотрудников'),
  -- Customer management
  ('b1000000-0000-0000-0000-000000000003', 'customers:read',      'customers',  'read',     'Просмотр клиентов'),
  ('b1000000-0000-0000-0000-000000000004', 'customers:manage',    'customers',  'manage',   'Управление клиентами');

-- =============================================================================
-- B. SYSTEM ROLES (6)
-- =============================================================================

INSERT INTO roles (id, name, description, is_system) VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin',              'Администратор — полный доступ к системе',                     true),
  ('00000000-0000-0000-0000-000000000002', 'customer',           'Клиент — каталог, заказы, профиль',                           true),
  ('00000000-0000-0000-0000-000000000003', 'content_manager',    'Контент-менеджер — управление каталогом и карточками товаров', true),
  ('00000000-0000-0000-0000-000000000004', 'order_manager',      'Менеджер по заказам — обработка заказов, статусы, возвраты',   true),
  ('00000000-0000-0000-0000-000000000005', 'support_specialist', 'Специалист поддержки — помощь клиентам, решение вопросов',     true),
  ('00000000-0000-0000-0000-000000000006', 'review_moderator',   'Модератор отзывов — проверка и публикация отзывов',           true);

-- =============================================================================
-- C. ROLE-PERMISSION ASSIGNMENTS
-- =============================================================================

-- admin: ALL 13 permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000001', id FROM permissions;

-- customer: read catalog, create/read orders, manage own profile
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000002', id FROM permissions
WHERE codename IN (
    'catalog:read',
    'orders:read',
    'reviews:read',
    'users:read', 'users:update', 'users:delete'
);

-- content_manager: full catalog + read reviews + read users
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000003', id FROM permissions
WHERE codename IN (
    'catalog:read', 'catalog:manage',
    'reviews:read',
    'users:read'
);

-- order_manager: full orders + returns + read catalog/users
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000004', id FROM permissions
WHERE codename IN (
    'orders:read', 'orders:manage',
    'returns:read', 'returns:manage',
    'catalog:read',
    'users:read'
);

-- support_specialist: read/update users + read orders/returns/catalog
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000005', id FROM permissions
WHERE codename IN (
    'users:read', 'users:update',
    'orders:read',
    'returns:read',
    'catalog:read'
);

-- review_moderator: moderate reviews + read catalog/users
INSERT INTO role_permissions (role_id, permission_id)
SELECT '00000000-0000-0000-0000-000000000006', id FROM permissions
WHERE codename IN (
    'reviews:read', 'reviews:moderate',
    'catalog:read',
    'users:read'
);

-- staff roles get customers:read
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name IN ('content_manager', 'order_manager', 'support_specialist', 'review_moderator')
  AND p.codename = 'customers:read';

-- =============================================================================
-- D. ROLE HIERARCHY
-- admin inherits all staff roles; staff roles inherit customer
-- =============================================================================

INSERT INTO role_hierarchy (parent_role_id, child_role_id) VALUES
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003'),  -- admin -> content_manager
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000004'),  -- admin -> order_manager
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000005'),  -- admin -> support_specialist
  ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000006'),  -- admin -> review_moderator
  ('00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000002'),  -- content_manager -> customer
  ('00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000002'),  -- order_manager -> customer
  ('00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002'),  -- support_specialist -> customer
  ('00000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-000000000002');  -- review_moderator -> customer

-- =============================================================================
-- E. DEV ADMIN USER
-- email: admin@loyality.dev  |  password: Admin123!
-- =============================================================================

DO $$
DECLARE
    v_admin_id UUID := '00000000-0000-0000-0000-000000000099';
BEGIN
    DELETE FROM staff_members WHERE id = v_admin_id;
    DELETE FROM customers WHERE id = v_admin_id;
    DELETE FROM users WHERE id = v_admin_id;
    DELETE FROM identities WHERE id = v_admin_id;

    INSERT INTO identities (id, type, account_type, is_active)
    VALUES (v_admin_id, 'LOCAL', 'STAFF', true);

    INSERT INTO local_credentials (identity_id, email, password_hash)
    VALUES (
        v_admin_id,
        'admin@loyality.dev',
        '$argon2id$v=19$m=65536,t=3,p=4$Vl1LrQ/C7dqMeuysMzvnfA$mNhTnlxQ31EinVbwyvkaYefUJ1CSa8EpzpUg1jjp+oQ'
    );

    -- Legacy users table (backward compat)
    INSERT INTO users (id, profile_email, first_name, last_name, phone)
    VALUES (v_admin_id, 'admin@loyality.dev', 'Admin', 'Dev', null);

    -- New staff_members table
    INSERT INTO staff_members (id, first_name, last_name, profile_email, invited_by)
    VALUES (v_admin_id, 'Admin', 'Dev', 'admin@loyality.dev', v_admin_id);

    INSERT INTO identity_roles (identity_id, role_id, assigned_by)
    VALUES (v_admin_id, '00000000-0000-0000-0000-000000000001', null);
END $$;

-- =============================================================================
-- F. CATALOG DATA
-- =============================================================================

-- Brands
INSERT INTO brands (id, name, slug) VALUES
  ('a1000000-0000-0000-0000-000000000001', 'Nike',    'nike'),
  ('a1000000-0000-0000-0000-000000000002', 'Adidas',  'adidas'),
  ('a1000000-0000-0000-0000-000000000003', 'Apple',   'apple'),
  ('a1000000-0000-0000-0000-000000000004', 'Samsung', 'samsung')
ON CONFLICT DO NOTHING;

-- Categories (from categories.json: 3 roots + 32 children)
DELETE FROM categories;

INSERT INTO categories (id, parent_id, full_slug, slug, level, name, sort_order) VALUES
  ('019cdbea-14dd-74d9-87bd-b96eb10a5812', null, 'clothing',    'clothing',    0, 'Одежда',     1),
  ('019cdbea-b86b-7253-aad4-5fd18c507b41', null, 'footwear',    'footwear',    0, 'Обувь',      2),
  ('019cdbea-f7fc-71ea-bf09-7bb6e857fd64', null, 'accessories', 'accessories', 0, 'Аксессуары', 3);

INSERT INTO categories (id, parent_id, full_slug, slug, level, name, sort_order) VALUES
  ('019cdbf2-dc56-7781-92fb-5a1657da2a49', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/tees',           'tees',           1, 'Футболки',      1),
  ('019cdbf2-f48b-7482-852a-3607d2955e57', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/hoodies',        'hoodies',        1, 'Худи',          2),
  ('019cdbf3-2184-7295-b9e0-c8099aabdc7d', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/zip-hoodies',    'zip-hoodies',    1, 'Зип-худи',      3),
  ('019cdbf3-3760-76e7-bd74-1b2f1043002d', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/jeans',          'jeans',          1, 'Джинсы',        4),
  ('019cdbf3-4cdc-7423-8c05-5d3f20bbc463', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/pants',          'pants',          1, 'Штаны',         5),
  ('019cdbf3-5fcf-7798-a034-46ac41dee905', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/shorts',         'shorts',         1, 'Шорты',         6),
  ('019cdbf3-7373-7269-a17a-eed6bf9f2286', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/tank-tops',      'tank-tops',      1, 'Майки',         7),
  ('019cdbf3-88fa-7443-b16c-bcbd48c4ee1c', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/long-sleeves',   'long-sleeves',   1, 'Лонгсливы',     8),
  ('019cdbf3-9f0f-70cf-b245-4a64bafe5350', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/sweatshirts',    'sweatshirts',    1, 'Свитшоты',      9),
  ('019cdbf3-bc06-703f-96ca-a7259d64d774', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/sweaters',       'sweaters',       1, 'Свитеры',      10),
  ('019cdbf3-ea78-74ac-a42e-469798ae7c48', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/shirts',         'shirts',         1, 'Рубашки',      11),
  ('019cdbf3-fdac-7743-a441-95dac98030ed', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/windbreakers',   'windbreakers',   1, 'Ветровки',     12),
  ('019cdbf4-127b-7107-b0e2-c8b015ee7752', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/bomber-jackets', 'bomber-jackets', 1, 'Бомберы',      13),
  ('019cdbf4-264f-707b-8cfc-a07c58285f97', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/jackets',        'jackets',        1, 'Куртки',       14),
  ('019cdbf4-39de-7259-b845-91568917294e', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/puffers',        'puffers',        1, 'Пуховики',     15),
  ('019cdbf4-5940-77ca-b478-eac54920d85e', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/vests',          'vests',          1, 'Жилеты',       16),
  ('019cdbf4-6cdc-76b7-a737-6a1d47f8a552', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/socks',          'socks',          1, 'Носки',        17),
  ('019cdbf4-8306-70ff-9288-99bacae667e1', '019cdbea-14dd-74d9-87bd-b96eb10a5812', 'clothing/underwear',      'underwear',      1, 'Нижнее бельё', 18);

INSERT INTO categories (id, parent_id, full_slug, slug, level, name, sort_order) VALUES
  ('019cdbf4-e987-75b9-aca8-8b2dd2c35314', '019cdbea-b86b-7253-aad4-5fd18c507b41', 'footwear/sneakers',     'sneakers',     1, 'Кроссовки', 1),
  ('019cdbf4-ff3e-7249-9623-9f8459a252eb', '019cdbea-b86b-7253-aad4-5fd18c507b41', 'footwear/canvas-shoes', 'canvas-shoes', 1, 'Кеды',      2),
  ('019cdbf5-112f-7019-8e69-2abdb8e0a4fc', '019cdbea-b86b-7253-aad4-5fd18c507b41', 'footwear/dress-shoes',  'dress-shoes',  1, 'Туфли',     3),
  ('019cdbf5-2847-7108-ac4e-5887aa40d9ea', '019cdbea-b86b-7253-aad4-5fd18c507b41', 'footwear/slides',       'slides',       1, 'Шлепанцы',  4),
  ('019cdbf5-3b0e-7666-9703-24e2a5853839', '019cdbea-b86b-7253-aad4-5fd18c507b41', 'footwear/boots',        'boots',        1, 'Ботинки',   5);

INSERT INTO categories (id, parent_id, full_slug, slug, level, name, sort_order) VALUES
  ('019cdbf5-4cc5-72de-9af0-eecd49d00e0c', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/bags',      'bags',      1, 'Сумки',     1),
  ('019cdbf5-608e-77a2-9c28-a44757e6a059', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/watches',   'watches',   1, 'Часы',      2),
  ('019cdbf5-7286-7126-95c8-fcfc1b268474', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/jewelry',   'jewelry',   1, 'Украшения', 3),
  ('019cdbf5-8320-75db-a4a2-bad1a20d9daf', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/backpacks', 'backpacks', 1, 'Рюкзаки',   4),
  ('019cdbf5-9636-730f-92e0-00462aec76cf', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/belts',     'belts',     1, 'Ремни',     5),
  ('019cdbf5-a86a-71fd-a2f8-b88bc13d7574', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/caps',      'caps',      1, 'Кепки',     6),
  ('019cdbf5-bc20-7312-9413-bdc229e8a13e', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/beanies',   'beanies',   1, 'Шапки',     7),
  ('019cdbf5-d39c-743a-a8a2-3d7c843f2a75', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/eyewear',   'eyewear',   1, 'Очки',      8),
  ('019cdbf5-ec62-771d-8a98-9aad741adab5', '019cdbea-f7fc-71ea-bf09-7bb6e857fd64', 'accessories/wallets',   'wallets',   1, 'Кошельки',  9);

COMMIT;
