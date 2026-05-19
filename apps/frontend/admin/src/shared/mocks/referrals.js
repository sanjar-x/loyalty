function isoWithOffset(baseIso, minutesBack) {
  const base = new Date(baseIso);
  const ms = base.getTime() - minutesBack * 60_000;
  return new Date(ms).toISOString();
}

const baseIso = '2026-01-17T19:13:00.000Z';

const items = [
  { slug: 'topor', label: 'topor' },
  { slug: 'pin', label: 'pin' },
  { slug: 'bio', label: 'bio' },
  { slug: 'ru', label: 'ru' },
  { slug: 'avito', label: 'avito' },
  { slug: 'reels', label: 'reels' },
  { slug: 'tiktok', label: 'tiktok' },
  { slug: 'vk', label: 'vk' },
  { slug: 'wbwin', label: 'wbwin' },
  { slug: 'inst', label: 'inst' },
  { slug: 'tg', label: 'tg' },
];

export const referralsSeed = items.map((it, index) => {
  const users = (index * 2350 + 55) % 14000;
  const usersDelta = index % 3 === 0 ? 0 : (index * 5) % 600;

  const orders = (index * 130 + 2) % 1200;
  const ordersDelta = index % 4 === 0 ? 0 : (index * 2) % 30;

  return {
    id: `ref-${it.slug}`,
    label: it.label,
    createdAt: isoWithOffset(baseIso, index * 1440),
    url: `https://t.me/loyaltymarketbot?start=${it.slug}`,
    users: { value: users, delta: usersDelta },
    orders: { value: orders, delta: ordersDelta },
  };
});
