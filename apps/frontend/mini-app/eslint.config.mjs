import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';

/**
 * Mini-app ESLint — `eslint-config-next` (core-web-vitals + react-hooks
 * bundled) ustiga ikkita qatlam (audit: frontend-main 2026-05-15, P1 #3;
 * admin appdagi sozlamalar bilan paritet):
 *
 *  1. react-hooks tuning — React Compiler diagnostikasi (runtime ta'siri
 *     yo'q, faqat optimizatsiya maslahatlari) o'chiriladi: shovqin kamayadi,
 *     `lint` baseline'i mazmunli bo'ladi.
 *  2. Layer boundary'lari — bir tomonlama import grafi
 *     `app → components → lib` `no-restricted-imports` orqali enforce
 *     qilinadi. Audit paytida 0 buzilish edi — endi linter ushlab turadi.
 */
const eslintConfig = defineConfig([
  ...nextVitals,

  // ── react-hooks tuning (admin bilan paritet) ──
  // `files` cheklovi majburiy: `react-hooks` plagini `eslint-config-next`
  // ichida aynan shu JS/TS glob bilan ro'yxatdan o'tgan. Cheklovsiz blok
  // `.json`/`.css` kabi fayllarga ham tarqaladi va u yerda plagin ko'rinmay
  // "plugin react-hooks not found" xatosini beradi (`off` qoidalar bundan
  // mustasno — ular plaginsiz ham ishlaydi, `warn`/`error` esa yo'q).
  {
    files: ['**/*.{js,jsx,mjs,ts,tsx,mts,cts}'],
    rules: {
      // Async `useEffect(() => { fetch().then(setState) }, [])` — kanonik
      // React pattern; React-19 strict qoidasi uni performance-smell deb
      // belgilaydi, lekin bu yerda trade-off maqbul.
      'react-hooks/set-state-in-effect': 'off',
      // Quyidagilar — React Compiler diagnostikasi: runtime ta'siri yo'q,
      // faqat optimizatsiya maslahatlari. Compiler joriy etilganda yoqiladi.
      'react-hooks/todo': 'off',
      'react-hooks/memo-dependencies': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/invariant': 'off',
      'react-hooks/immutability': 'off',
      // `react-hooks/refs` — render paytida ref o'qilishini ushlaydi (haqiqiy
      // kod hidi, lekin runtime'da darhol sinmaydi). `eslint-config-next` uni
      // `error` qiladi; audit #1 (god-komponentlar) hal qilguncha `warn` —
      // baseline'ni bloklamaydi, lekin Problems panelida ko'rinib turadi
      // (admin appdagi react-hooks=warn siyosati bilan paritet).
      'react-hooks/refs': 'warn',
      // `@next/next/no-img-element` — mini-app butun bo'ylab `<img>` ishlatadi
      // (Telegram Mini App: remote/blob rasm manbalari, `next/image` overhead'i
      // bu kontekstda oqlanmaydi). 135 ogohlantirish — sof shovqin, haqiqiy
      // signallarni (`exhaustive-deps`) ko'mib yuboradi. `next/image` ga ko'chish
      // alohida, ataylab qilinadigan ish — o'shangacha `off`.
      '@next/next/no-img-element': 'off',
    },
  },

  // ── Layer boundary'lari: app → components → lib (bir tomonlama graf) ──
  {
    files: ['lib/**/*.{js,jsx,mjs,cjs,ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/components', '@/components/**', '@/app', '@/app/**'],
              message:
                'lib/ — pastki qatlam: components/ yoki app/ ni import qila olmaydi. Faqat lib/ ichidan import qiling.',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['components/**/*.{js,jsx,mjs,cjs,ts,tsx}'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/app', '@/app/**'],
              message:
                "components/ — app/ ga bog'liq bo'la olmaydi. Umumiy kod lib/ ga ko'tariladi.",
            },
          ],
        },
      ],
    },
  },

  // Override default ignores of eslint-config-next.
  globalIgnores(['.next/**', 'out/**', 'build/**']),
]);

export default eslintConfig;
