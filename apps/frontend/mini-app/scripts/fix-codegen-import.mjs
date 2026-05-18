/**
 * Post-codegen fix: rtk-query-codegen-openapi генерирует относительный путь
 * `from '../base-api/baseApi'` (или `'../baseApi'` в старой раскладке —
 * см. историю). С relative-импортом TypeScript (bundler resolver) почему-то
 * теряет типы build.mutation<X,Y>, выдаёт TS2347. Тот же файл импортируемый
 * через path-mapped alias `@/shared/api/base-api/baseApi` — типизируется
 * корректно.
 *
 * Этот скрипт запускается автоматически после `npm run api:gen` и заменяет
 * импорт-строку на path-mapped. Idempotent. Tolerant к single/double quotes
 * и к разным relative-путям (на случай если apiFile/outputFile поменяются
 * в openapi.config.cjs).
 */
import { readFileSync, writeFileSync } from 'node:fs';

const PATH = 'src/shared/api/codegen/api.ts';
const NEW = `import { baseApi as api } from '@/shared/api/base-api/baseApi';`;

// Матчим любой relative import baseApi:
//   import { baseApi as api } from '../baseApi';
//   import { baseApi as api } from "../base-api/baseApi";
//   import { baseApi as api } from '../../shared/api/base-api/baseApi';
// — любые кавычки, любая относительная глубина.
const RELATIVE_IMPORT_RE =
  /^import \{ baseApi as api \} from ['"](\.\.?\/[^'"]+baseApi)['"];?$/m;
const PATH_MAPPED_RE =
  /^import \{ baseApi as api \} from ['"]@\/shared\/api\/base-api\/baseApi['"];?$/m;

const src = readFileSync(PATH, 'utf8');

if (PATH_MAPPED_RE.test(src)) {
  console.log(`[fix-codegen-import] ${PATH} — already using path-mapped import (no-op)`);
  process.exit(0);
}

const m = src.match(RELATIVE_IMPORT_RE);
if (!m) {
  console.error(`[fix-codegen-import] FAIL: ${PATH} does not contain the expected import line.`);
  console.error('  Expected (regex):', RELATIVE_IMPORT_RE.source);
  console.error('  Did rtk-query-codegen-openapi change its output format,');
  console.error('  or did openapi.config.cjs apiFile/outputFile move?');
  process.exit(1);
}

writeFileSync(PATH, src.replace(m[0], NEW), 'utf8');
console.log(`[fix-codegen-import] ${PATH} → path-mapped import OK`);
console.log(`  was: ${m[0]}`);
console.log(`  now: ${NEW}`);
