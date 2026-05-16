/**
 * @rtk-query/codegen-openapi config — openapi.json ni o'qib `lib/store/__generated__/api.ts`
 * faylida RTKQ endpointlari va ularning Request/Response tiplarini chiqaradi.
 *
 * Generatsiya qoidalari:
 *  • `apiFile` — bizning `baseApi` instansi (lib/store/baseApi.js)
 *  • `apiImport` — `baseApi` named export
 *  • `outputFile` — `lib/store/__generated__/api.ts` (gitda saqlanadi, drift CI bilan tekshiriladi)
 *  • `hooks: true` — useGet*Query / useGet*Mutation hook'lari
 *  • `tag: true` — `tags: ["Foo"]` ni `providesTags`/`invalidatesTags` ga aylantiradi
 *  • `flattenArg: false` — har endpoint'ga `arg` typed object beradi (Pydantic-style)
 *
 * Chiqishni qo'lda tahrirlamang. O'zgartirish uchun `npm run api:gen` ishga tushiring.
 */
module.exports = {
  schemaFile: './openapi.json',
  apiFile: './lib/store/baseApi.js',
  apiImport: 'baseApi',
  outputFile: './lib/store/__generated__/api.ts',
  exportName: 'generatedApi',
  hooks: { queries: true, lazyQueries: true, mutations: true },
  tag: true,
  flattenArg: false,
};
