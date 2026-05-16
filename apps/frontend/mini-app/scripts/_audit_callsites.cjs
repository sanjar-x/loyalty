const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const apiSrc = fs.readFileSync(path.join(root, 'lib/store/api.js'), 'utf8');

// api.js'da export qilingan barcha nomlar
const exportedNames = new Set();
for (const m of apiSrc.matchAll(/^export\s+(?:const|function)\s+(\w+)/gm)) {
  exportedNames.add(m[1]);
}
for (const m of apiSrc.matchAll(/^export\s*\{([^}]+)\}/gm)) {
  m[1].split(',').forEach((n) => {
    const clean = n.split(/\s+as\s+/)[0].trim();
    if (clean) exportedNames.add(clean);
  });
}

// Call site'lardan @/lib/store/api importlarini topish
function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    if (name === 'node_modules' || name === '.next' || name === '__generated__') continue;
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) walk(full, out);
    else if (/\.(jsx?|tsx?)$/.test(name)) out.push(full);
  }
  return out;
}

const allFiles = [
  ...walk(path.join(root, 'app')),
  ...walk(path.join(root, 'components')),
  ...walk(path.join(root, 'lib')),
];

// 1. import qilinganlarni yig'ish
const importsByFile = new Map();
const allImported = new Set();
const importRe = /import\s+(?:[^'"]+\s+from\s+)?['"]@\/lib\/store\/api['"]/g;
for (const file of allFiles) {
  const src = fs.readFileSync(file, 'utf8');
  // `{` ichidagi `}` boshqa `{`siz bo'lishi sharti — react+api ikki importni
  // bir blokga yig'ishni oldini oladi (lazy backtrack tuzog'i).
  const importRe2 = /import\s*\{([^{}]*?)\}\s*from\s*["']@\/lib\/store\/api["']/g;
  const collected = [];
  for (const m of src.matchAll(importRe2)) {
    m[1]
      .split(',')
      .map((n) =>
        n
          .trim()
          .split(/\s+as\s+/)[0]
          .replace(/\s+/g, '')
      )
      .filter(Boolean)
      .forEach((n) => collected.push(n));
  }
  if (collected.length === 0) continue;
  const names = collected;
  importsByFile.set(file.replace(root + path.sep, ''), names);
  names.forEach((n) => allImported.add(n));
}

// 2. import qilingan, lekin export bo'lmagan
const missing = [...allImported].filter((n) => !exportedNames.has(n));

console.log('=== Call-site audit ===');
console.log('api.js exportlari soni:    ', exportedNames.size);
console.log('Importlar yagona nomlari:  ', allImported.size);
console.log("Importi bor, eksporti yo'q:", missing.length);
if (missing.length) {
  console.log('\nMuammoli nomlar:');
  for (const name of missing) {
    console.log('  - ' + name);
    for (const [file, names] of importsByFile) {
      if (names.includes(name)) console.log('       ↳ ' + file);
    }
  }
}

// 3. teskari: api.js'da export bor, lekin hech kim ishlatmaydi (dead code)
const unused = [...exportedNames].filter((n) => !allImported.has(n));
console.log('\nExport bor, ishlatilmaydi:', unused.length);
if (unused.length) {
  console.log('Yetim exportlar:');
  unused.forEach((n) => console.log('  - ' + n));
}
