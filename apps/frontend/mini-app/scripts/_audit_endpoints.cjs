const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const apiSrc = fs.readFileSync(path.join(root, 'lib/store/api.js'), 'utf8');
const genSrc = fs.readFileSync(path.join(root, 'lib/store/__generated__/api.ts'), 'utf8');

// 1. enhanceEndpoints ichidagi kalitlar
const enhanceMatch = apiSrc.match(
  /enhanceEndpoints\(\{[\s\S]*?endpoints:\s*\{([\s\S]*?)\n\s{2}\},\s*\}\)/
);
const block = enhanceMatch ? enhanceMatch[1] : '';
const enhanceKeys = [...block.matchAll(/^\s{4}(\w+):\s*\{/gm)].map((m) => m[1]);

// 2. Generated endpoint nomlari
const genKeys = new Set(
  [...genSrc.matchAll(/^\s{6}(\w+):\s*build\.(query|mutation)</gm)].map((m) => m[1])
);

// 3. Mismatch
const missing = enhanceKeys.filter((k) => !genKeys.has(k));

console.log('=== enhanceEndpoints audit ===');
console.log('enhanceEndpoints kalit soni:', enhanceKeys.length);
console.log('Generated endpoint soni:    ', genKeys.size);
console.log('MISSING in generated:       ', missing.length);
if (missing.length) {
  console.log("Yo'qolgan kalitlar:");
  missing.forEach((k) => console.log('  - ' + k));
}

// 4. api.js dagi enhancedApi.useXxx chaqiruvlar — generatedda bormi?
const hookCalls = [...apiSrc.matchAll(/enhancedApi\.(use\w+)/g)].map((m) => m[1]);
const uniqueHooks = [...new Set(hookCalls)];
const generatedHooks = new Set([...genSrc.matchAll(/^\s+(use\w+),?\s*$/gm)].map((m) => m[1]));
const missingHooks = uniqueHooks.filter((h) => !generatedHooks.has(h));

console.log('\n=== Hook re-export audit ===');
console.log('api.js `enhancedApi.useXxx` ishlatishlari:', uniqueHooks.length);
console.log('Generated hook soni:                       ', generatedHooks.size);
console.log('MISSING hooks:                              ', missingHooks.length);
if (missingHooks.length) {
  console.log("Yo'qolgan hooklar:");
  missingHooks.forEach((h) => console.log('  - ' + h));
}
