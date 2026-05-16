/**
 * LAN IPv4 manzillarini aniqlash uchun yordamchi.
 *
 * `next.config.js` dagi `allowedDevOrigins` ga avtomatik to'ldirish uchun
 * ishlatiladi — DHCP tomonidan IP o'zgarganda ham qo'lda tahrirlash kerak emas.
 *
 * Returns: string[] — faqat xususiy tarmoq (RFC1918) IPv4 manzillari.
 *
 * Qamrov:
 *   10.0.0.0      – 10.255.255.255
 *   172.16.0.0    – 172.31.255.255
 *   192.168.0.0   – 192.168.255.255
 *   169.254.0.0   – 169.254.255.255 (link-local, ba'zida foydali)
 */
const os = require('node:os');

function isPrivateIPv4(ip) {
  const parts = ip.split('.').map(Number);
  if (parts.length !== 4 || parts.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) {
    return false;
  }
  const [a, b] = parts;
  if (a === 10) return true;
  if (a === 192 && b === 168) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 169 && b === 254) return true;
  return false;
}

function detectLanIPv4() {
  const ifaces = os.networkInterfaces();
  const ips = new Set();

  for (const list of Object.values(ifaces)) {
    if (!list) continue;
    for (const iface of list) {
      if (iface.family !== 'IPv4' && iface.family !== 4) continue;
      if (iface.internal) continue;
      if (!isPrivateIPv4(iface.address)) continue;
      ips.add(iface.address);
    }
  }

  return [...ips].sort();
}

module.exports = { detectLanIPv4, isPrivateIPv4 };

// Skript to'g'ridan-to'g'ri ishga tushirilganda — aniqlangan IP'larni chop etish
if (require.main === module) {
  const ips = detectLanIPv4();
  if (ips.length === 0) {
    console.error('LAN IPv4 manzillari topilmadi.');
    process.exit(1);
  }
  for (const ip of ips) console.log(ip);
}
