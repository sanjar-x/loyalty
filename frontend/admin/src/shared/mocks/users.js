function isoWithOffset(baseIso, minutesBack) {
  const base = new Date(baseIso);
  const ms = base.getTime() - minutesBack * 60_000;
  return new Date(ms).toISOString();
}

const baseIso = '2026-02-18T07:13:00.000Z';

const handles = [
  '@evgeny',
  '@alina',
  '@darya',
  '@timur',
  '@maxim',
  '@sofia',
  '@nikita',
  '@arina',
  '@maria',
  '@daniel',
  '@aziza',
  '@said',
  '@karina',
  '@oleg',
  '@dilshod',
  '@anya',
  '@pavel',
  '@ulugbek',
  '@inna',
  '@roman',
];

const sources = ['start-bio', 'start-site', 'start-topor', 'start-pinned'];

export const usersSeed = Array.from({ length: 57 }, (_, index) => {
  const handle = handles[index % handles.length];
  const source = sources[index % sources.length];
  const minutesBack = index * 37;

  const followers = (index * 3) % 9;
  const followersDelta = index % 3 === 0 ? 0 : index % 4 === 0 ? 1 : 3;

  const orders = (index * 2) % 7;
  const ordersDelta = index % 2 === 0 ? 0 : 1;

  return {
    id: `usr-${1000 + index}`,
    handle,
    userId: String(707653394 + index),
    avatar: '/avatars/default.png',
    createdAt: isoWithOffset(baseIso, minutesBack),
    source,
    followers: { value: followers, delta: followersDelta },
    orders: { value: orders, delta: ordersDelta },
  };
});
