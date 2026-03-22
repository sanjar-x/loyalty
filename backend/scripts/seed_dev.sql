-- =============================================================================
-- seed_dev.sql — Dev database seed script
-- =============================================================================
-- Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING).
-- IAM roles & permissions are managed by Alembic migration (seed_iam).
-- This script seeds ONLY dev-specific data on top of migration data.
--
-- Usage:
--   docker exec -i postgres psql -U postgres -d enterprise < scripts/seed_dev.sql
--
-- Sections:
--   A. Dev admin user (admin@loyality.dev / Admin123!)
--   B. Catalog data (brands + categories)
-- =============================================================================
BEGIN;

-- =============================================================================
-- A. DEV ADMIN USER
-- email: admin@loyality.dev  |  password: Admin123!
-- =============================================================================
DO $ $ DECLARE v_admin_id UUID := '00000000-0000-0000-0000-000000000099';

BEGIN -- Clean up existing dev admin (dependency order)
DELETE FROM
  identity_roles
WHERE
  identity_id = v_admin_id;

DELETE FROM
  session_roles
WHERE
  session_id IN (
    SELECT
      id
    FROM
      sessions
    WHERE
      identity_id = v_admin_id
  );

DELETE FROM
  sessions
WHERE
  identity_id = v_admin_id;

DELETE FROM
  local_credentials
WHERE
  identity_id = v_admin_id;

DELETE FROM
  linked_accounts
WHERE
  identity_id = v_admin_id;

DELETE FROM
  staff_members
WHERE
  id = v_admin_id;

DELETE FROM
  customers
WHERE
  id = v_admin_id;

DELETE FROM
  identities
WHERE
  id = v_admin_id;

INSERT INTO
  identities (id, primary_auth_method, account_type, is_active)
VALUES
  (v_admin_id, 'LOCAL', 'STAFF', true);

INSERT INTO
  local_credentials (identity_id, email, password_hash)
VALUES
  (
    v_admin_id,
    'admin@loyality.dev',
    '$argon2id$v=19$m=65536,t=3,p=4$Vl1LrQ/C7dqMeuysMzvnfA$mNhTnlxQ31EinVbwyvkaYefUJ1CSa8EpzpUg1jjp+oQ'
  );

INSERT INTO
  staff_members (
    id,
    first_name,
    last_name,
    profile_email,
    invited_by
  )
VALUES
  (
    v_admin_id,
    'Admin',
    'Dev',
    'admin@loyality.dev',
    v_admin_id
  );

-- Assign admin role
INSERT INTO
  identity_roles (identity_id, role_id, assigned_by)
VALUES
  (
    v_admin_id,
    '00000000-0000-0000-0000-000000000001',
    null
  );

END $ $;

-- =============================================================================
-- B. CATALOG DATA
-- =============================================================================
-- Brands
INSERT INTO
  brands (id, name, slug)
VALUES
  (
    'a1000000-0000-0000-0000-000000000001',
    'Nike',
    'nike'
  ),
  (
    'a1000000-0000-0000-0000-000000000002',
    'Adidas',
    'adidas'
  ),
  (
    'a1000000-0000-0000-0000-000000000003',
    'Apple',
    'apple'
  ),
  (
    'a1000000-0000-0000-0000-000000000004',
    'Samsung',
    'samsung'
  ) ON CONFLICT DO NOTHING;

-- Categories (3 roots + 32 children)
DELETE FROM
  categories;

INSERT INTO
  categories (
    id,
    parent_id,
    full_slug,
    slug,
    level,
    name,
    sort_order
  )
VALUES
  (
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    null,
    'clothing',
    'clothing',
    0,
    'Одежда',
    1
  ),
  (
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    null,
    'footwear',
    'footwear',
    0,
    'Обувь',
    2
  ),
  (
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    null,
    'accessories',
    'accessories',
    0,
    'Аксессуары',
    3
  );

INSERT INTO
  categories (
    id,
    parent_id,
    full_slug,
    slug,
    level,
    name,
    sort_order
  )
VALUES
  (
    '019cdbf2-dc56-7781-92fb-5a1657da2a49',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/tees',
    'tees',
    1,
    'Футболки',
    1
  ),
  (
    '019cdbf2-f48b-7482-852a-3607d2955e57',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/hoodies',
    'hoodies',
    1,
    'Худи',
    2
  ),
  (
    '019cdbf3-2184-7295-b9e0-c8099aabdc7d',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/zip-hoodies',
    'zip-hoodies',
    1,
    'Зип-худи',
    3
  ),
  (
    '019cdbf3-3760-76e7-bd74-1b2f1043002d',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/jeans',
    'jeans',
    1,
    'Джинсы',
    4
  ),
  (
    '019cdbf3-4cdc-7423-8c05-5d3f20bbc463',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/pants',
    'pants',
    1,
    'Штаны',
    5
  ),
  (
    '019cdbf3-5fcf-7798-a034-46ac41dee905',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/shorts',
    'shorts',
    1,
    'Шорты',
    6
  ),
  (
    '019cdbf3-7373-7269-a17a-eed6bf9f2286',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/tank-tops',
    'tank-tops',
    1,
    'Майки',
    7
  ),
  (
    '019cdbf3-88fa-7443-b16c-bcbd48c4ee1c',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/long-sleeves',
    'long-sleeves',
    1,
    'Лонгсливы',
    8
  ),
  (
    '019cdbf3-9f0f-70cf-b245-4a64bafe5350',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/sweatshirts',
    'sweatshirts',
    1,
    'Свитшоты',
    9
  ),
  (
    '019cdbf3-bc06-703f-96ca-a7259d64d774',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/sweaters',
    'sweaters',
    1,
    'Свитеры',
    10
  ),
  (
    '019cdbf3-ea78-74ac-a42e-469798ae7c48',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/shirts',
    'shirts',
    1,
    'Рубашки',
    11
  ),
  (
    '019cdbf3-fdac-7743-a441-95dac98030ed',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/windbreakers',
    'windbreakers',
    1,
    'Ветровки',
    12
  ),
  (
    '019cdbf4-127b-7107-b0e2-c8b015ee7752',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/bomber-jackets',
    'bomber-jackets',
    1,
    'Бомберы',
    13
  ),
  (
    '019cdbf4-264f-707b-8cfc-a07c58285f97',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/jackets',
    'jackets',
    1,
    'Куртки',
    14
  ),
  (
    '019cdbf4-39de-7259-b845-91568917294e',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/puffers',
    'puffers',
    1,
    'Пуховики',
    15
  ),
  (
    '019cdbf4-5940-77ca-b478-eac54920d85e',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/vests',
    'vests',
    1,
    'Жилеты',
    16
  ),
  (
    '019cdbf4-6cdc-76b7-a737-6a1d47f8a552',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/socks',
    'socks',
    1,
    'Носки',
    17
  ),
  (
    '019cdbf4-8306-70ff-9288-99bacae667e1',
    '019cdbea-14dd-74d9-87bd-b96eb10a5812',
    'clothing/underwear',
    'underwear',
    1,
    'Нижнее бельё',
    18
  );

INSERT INTO
  categories (
    id,
    parent_id,
    full_slug,
    slug,
    level,
    name,
    sort_order
  )
VALUES
  (
    '019cdbf4-e987-75b9-aca8-8b2dd2c35314',
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    'footwear/sneakers',
    'sneakers',
    1,
    'Кроссовки',
    1
  ),
  (
    '019cdbf4-ff3e-7249-9623-9f8459a252eb',
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    'footwear/canvas-shoes',
    'canvas-shoes',
    1,
    'Кеды',
    2
  ),
  (
    '019cdbf5-112f-7019-8e69-2abdb8e0a4fc',
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    'footwear/dress-shoes',
    'dress-shoes',
    1,
    'Туфли',
    3
  ),
  (
    '019cdbf5-2847-7108-ac4e-5887aa40d9ea',
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    'footwear/slides',
    'slides',
    1,
    'Шлепанцы',
    4
  ),
  (
    '019cdbf5-3b0e-7666-9703-24e2a5853839',
    '019cdbea-b86b-7253-aad4-5fd18c507b41',
    'footwear/boots',
    'boots',
    1,
    'Ботинки',
    5
  );

INSERT INTO
  categories (
    id,
    parent_id,
    full_slug,
    slug,
    level,
    name,
    sort_order
  )
VALUES
  (
    '019cdbf5-4cc5-72de-9af0-eecd49d00e0c',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/bags',
    'bags',
    1,
    'Сумки',
    1
  ),
  (
    '019cdbf5-608e-77a2-9c28-a44757e6a059',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/watches',
    'watches',
    1,
    'Часы',
    2
  ),
  (
    '019cdbf5-7286-7126-95c8-fcfc1b268474',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/jewelry',
    'jewelry',
    1,
    'Украшения',
    3
  ),
  (
    '019cdbf5-8320-75db-a4a2-bad1a20d9daf',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/backpacks',
    'backpacks',
    1,
    'Рюкзаки',
    4
  ),
  (
    '019cdbf5-9636-730f-92e0-00462aec76cf',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/belts',
    'belts',
    1,
    'Ремни',
    5
  ),
  (
    '019cdbf5-a86a-71fd-a2f8-b88bc13d7574',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/caps',
    'caps',
    1,
    'Кепки',
    6
  ),
  (
    '019cdbf5-bc20-7312-9413-bdc229e8a13e',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/beanies',
    'beanies',
    1,
    'Шапки',
    7
  ),
  (
    '019cdbf5-d39c-743a-a8a2-3d7c843f2a75',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/eyewear',
    'eyewear',
    1,
    'Очки',
    8
  ),
  (
    '019cdbf5-ec62-771d-8a98-9aad741adab5',
    '019cdbea-f7fc-71ea-bf09-7bb6e857fd64',
    'accessories/wallets',
    'wallets',
    1,
    'Кошельки',
    9
  );

COMMIT;
