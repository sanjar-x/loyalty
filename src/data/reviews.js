import dayjs from '@/lib/dayjs';
import { ordersSeed } from '@/data/orders';
import { productsSeed } from '@/data/products';

const users = [
  { id: 'usr-1', name: 'evgeny' },
  { id: 'usr-2', name: 'maria' },
  { id: 'usr-3', name: 'artem' },
  { id: 'usr-4', name: 'dina' },
  { id: 'usr-5', name: 'sergey' },
  { id: 'usr-6', name: 'alina' },
  { id: 'usr-7', name: 'timur' },
  { id: 'usr-8', name: 'kira' },
];

const prosOptions = [
  'стильно, классика которую можно носить',
  'приятная ткань и ровные швы',
  'хорошо сидит, размер совпал',
  'качественная фурнитура',
  'цвет как на фото',
];

const consOptions = [
  'клей на подошве',
  'долгая доставка',
  'не подошёл размер',
  'упаковка могла быть лучше',
  'нет',
];

const commentOptions = [
  'клей на подошве',
  'клей на подошве, долгая доставка и немного не подошёл размер',
  'в целом доволен, возьму ещё',
  '',
];

const productFallbackImage = '/products/hoodie-black.svg';

function pick(list, index) {
  if (!list.length) return null;
  return list[index % list.length];
}

function clampInt(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function ratingForIndex(index) {
  // Deterministic distribution with a bias to 4-5 like in real marketplaces.
  // 0..19 → [5,5,5,4,4,5,4,5,3,4,5,5,4,5,4,3,2,4,5,1]
  const table = [5, 5, 5, 4, 4, 5, 4, 5, 3, 4, 5, 5, 4, 5, 4, 3, 2, 4, 5, 1];
  return table[index % table.length];
}

function generateReview(index) {
  const product = pick(productsSeed, index);
  const user = pick(users, index);
  const order = pick(ordersSeed, index);

  const rating = ratingForIndex(index);
  const createdAt = dayjs('2026-01-20T12:00:00+03:00')
    .subtract(index % 60, 'day')
    .subtract((index * 13) % 24, 'hour')
    .toISOString();

  const pros = pick(prosOptions, index);
  const cons = pick(consOptions, index * 3);
  const comment = pick(commentOptions, index * 5);

  const hasPhotos = index % 3 === 0;
  const photos = hasPhotos
    ? [
        product?.image ?? productFallbackImage,
        pick(productsSeed, index + 2)?.image ?? '/products/sneakers-white.svg',
        pick(productsSeed, index + 5)?.image ?? '/products/bag-black.svg',
      ].filter(Boolean)
    : [];

  const sourceTag = product?.source === 'stock' ? 'Из наличия' : 'Из Китая';
  const tags = [sourceTag];
  if (product?.isOriginal) tags.push('Оригинал');

  const orderNumber = order?.orderNumber ?? String(40000000000 + index);

  return {
    id: `rev-${String(index + 1).padStart(4, '0')}`,
    createdAt,
    rating,
    pros,
    cons,
    comment,
    photos,
    user: {
      id: user?.id ?? `usr-${index}`,
      name: user?.name ?? 'user',
    },
    product: {
      id: product?.id ?? `prd-${index}`,
      brand: product?.brand ?? 'Supreme',
      title: product?.title ?? 'Товар',
      size: pick(product?.sizes ?? ['S', 'M', 'L'], index * 2),
      image: product?.image ?? productFallbackImage,
      tags,
    },
    order: {
      id: order?.id ?? `ord-${index}`,
      number: orderNumber,
      createdAt: order?.createdAt ?? createdAt,
    },
  };
}

export function generateReviewsSeed(count = 3432) {
  const safeCount = clampInt(count, 1, 10000);
  return Array.from({ length: safeCount }, (_, index) => generateReview(index));
}

export const reviewsSeed = generateReviewsSeed(3432);
