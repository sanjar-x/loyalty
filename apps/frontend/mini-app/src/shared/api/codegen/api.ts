import { baseApi as api } from '@/shared/api/base-api/baseApi';
export const addTagTypes = [
  'Geo',
  'Admin / Geo',
  'Authentication',
  'Invitations',
  'Profile',
  'Profile / Account',
  'Admin / IAM',
  'Admin / Staff',
  'Admin / Customers',
  'Admin / Suppliers',
  'Storefront / Categories',
  'Storefront / Taxonomy',
  'Storefront / Products',
  'Storefront / Search',
  'Storefront / Trending',
  'Storefront / For You',
  'Admin / Catalog / Brands',
  'Admin / Catalog / Categories',
  'Admin / Catalog / Attributes',
  'Admin / Catalog / Attribute Groups',
  'Admin / Catalog / Attribute Values',
  'Admin / Catalog / Attribute Templates',
  'Admin / Catalog / Products',
  'Admin / Catalog / Variants',
  'Admin / Catalog / SKUs',
  'Admin / Catalog / Product Attributes',
  'Admin / Catalog / Product Media',
  'Admin / Pricing / Variables',
  'Admin / Pricing / Contexts',
  'Admin / Pricing / Formulas',
  'Admin / Pricing / Preview',
  'Admin / Pricing / Products',
  'Admin / Pricing / Suppliers',
  'Admin / Pricing / Supplier-Type Mapping',
  'Admin / Pricing / Categories',
  'Admin / Pricing / Recompute',
  'Admin / Analytics',
  'Cart',
  'Favorites',
  'Admin / Media',
  'Storefront / Logistics',
  'Admin / Logistics / Provider Accounts',
  'Admin / Logistics / Shipments',
  'Admin / Logistics / CDEK',
  'Webhooks / Logistics',
  'Payments',
  'Webhooks / Payments',
  'Recipients',
  'Orders',
  'Admin / Orders',
  'Webhooks / DobroPost',
  'System',
] as const;
const injectedRtkApi = api
  .enhanceEndpoints({
    addTagTypes,
  })
  .injectEndpoints({
    endpoints: (build) => ({
      listCountriesApiV1GeoCountriesGet: build.query<
        ListCountriesApiV1GeoCountriesGetApiResponse,
        ListCountriesApiV1GeoCountriesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/countries`,
          params: {
            lang: queryArg.lang,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      listCurrenciesApiV1GeoCurrenciesGet: build.query<
        ListCurrenciesApiV1GeoCurrenciesGetApiResponse,
        ListCurrenciesApiV1GeoCurrenciesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/currencies`,
          params: {
            lang: queryArg.lang,
            includeInactive: queryArg.includeInactive,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      listLanguagesApiV1GeoLanguagesGet: build.query<
        ListLanguagesApiV1GeoLanguagesGetApiResponse,
        ListLanguagesApiV1GeoLanguagesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/languages`,
          params: {
            includeInactive: queryArg.includeInactive,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      getCountryApiV1GeoCountriesAlpha2Get: build.query<
        GetCountryApiV1GeoCountriesAlpha2GetApiResponse,
        GetCountryApiV1GeoCountriesAlpha2GetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/countries/${queryArg.alpha2}`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Geo'],
      }),
      getCurrencyApiV1GeoCurrenciesCodeGet: build.query<
        GetCurrencyApiV1GeoCurrenciesCodeGetApiResponse,
        GetCurrencyApiV1GeoCurrenciesCodeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/currencies/${queryArg.code}`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Geo'],
      }),
      getLanguageApiV1GeoLanguagesCodeGet: build.query<
        GetLanguageApiV1GeoLanguagesCodeGetApiResponse,
        GetLanguageApiV1GeoLanguagesCodeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/languages/${queryArg.code}`,
        }),
        providesTags: ['Geo'],
      }),
      getSubdivisionApiV1GeoSubdivisionsCodeGet: build.query<
        GetSubdivisionApiV1GeoSubdivisionsCodeGetApiResponse,
        GetSubdivisionApiV1GeoSubdivisionsCodeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/subdivisions/${queryArg.code}`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Geo'],
      }),
      listCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGet: build.query<
        ListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetApiResponse,
        ListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/countries/${queryArg.countryCode}/currencies`,
          params: {
            lang: queryArg.lang,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      listSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGet: build.query<
        ListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetApiResponse,
        ListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/countries/${queryArg.countryCode}/subdivisions`,
          params: {
            lang: queryArg.lang,
            search: queryArg.search,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      getDistrictApiV1GeoDistrictsDistrictIdGet: build.query<
        GetDistrictApiV1GeoDistrictsDistrictIdGetApiResponse,
        GetDistrictApiV1GeoDistrictsDistrictIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/districts/${queryArg.districtId}`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Geo'],
      }),
      listDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGet: build.query<
        ListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetApiResponse,
        ListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/geo/subdivisions/${queryArg.subdivisionCode}/districts`,
          params: {
            lang: queryArg.lang,
            search: queryArg.search,
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Geo'],
      }),
      createCountryApiV1AdminGeoCountriesPost: build.mutation<
        CreateCountryApiV1AdminGeoCountriesPostApiResponse,
        CreateCountryApiV1AdminGeoCountriesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/countries`,
          method: 'POST',
          body: queryArg.createCountryRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateCountryApiV1AdminGeoCountriesAlpha2Patch: build.mutation<
        UpdateCountryApiV1AdminGeoCountriesAlpha2PatchApiResponse,
        UpdateCountryApiV1AdminGeoCountriesAlpha2PatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/countries/${queryArg.alpha2}`,
          method: 'PATCH',
          body: queryArg.updateCountryRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteCountryApiV1AdminGeoCountriesAlpha2Delete: build.mutation<
        DeleteCountryApiV1AdminGeoCountriesAlpha2DeleteApiResponse,
        DeleteCountryApiV1AdminGeoCountriesAlpha2DeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/countries/${queryArg.alpha2}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPut: build.mutation<
        UpsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPutApiResponse,
        UpsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/countries/${queryArg.alpha2}/translations`,
          method: 'PUT',
          body: queryArg.upsertCountryTranslationsRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      setCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPut: build.mutation<
        SetCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPutApiResponse,
        SetCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/countries/${queryArg.alpha2}/currencies`,
          method: 'PUT',
          body: queryArg.setCountryCurrenciesRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      createCurrencyApiV1AdminGeoCurrenciesPost: build.mutation<
        CreateCurrencyApiV1AdminGeoCurrenciesPostApiResponse,
        CreateCurrencyApiV1AdminGeoCurrenciesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/currencies`,
          method: 'POST',
          body: queryArg.createCurrencyRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateCurrencyApiV1AdminGeoCurrenciesCodePatch: build.mutation<
        UpdateCurrencyApiV1AdminGeoCurrenciesCodePatchApiResponse,
        UpdateCurrencyApiV1AdminGeoCurrenciesCodePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/currencies/${queryArg.code}`,
          method: 'PATCH',
          body: queryArg.updateCurrencyRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteCurrencyApiV1AdminGeoCurrenciesCodeDelete: build.mutation<
        DeleteCurrencyApiV1AdminGeoCurrenciesCodeDeleteApiResponse,
        DeleteCurrencyApiV1AdminGeoCurrenciesCodeDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/currencies/${queryArg.code}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPut: build.mutation<
        UpsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPutApiResponse,
        UpsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/currencies/${queryArg.code}/translations`,
          method: 'PUT',
          body: queryArg.upsertCurrencyTranslationsRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      createLanguageApiV1AdminGeoLanguagesPost: build.mutation<
        CreateLanguageApiV1AdminGeoLanguagesPostApiResponse,
        CreateLanguageApiV1AdminGeoLanguagesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/languages`,
          method: 'POST',
          body: queryArg.createLanguageRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateLanguageApiV1AdminGeoLanguagesCodePatch: build.mutation<
        UpdateLanguageApiV1AdminGeoLanguagesCodePatchApiResponse,
        UpdateLanguageApiV1AdminGeoLanguagesCodePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/languages/${queryArg.code}`,
          method: 'PATCH',
          body: queryArg.updateLanguageRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteLanguageApiV1AdminGeoLanguagesCodeDelete: build.mutation<
        DeleteLanguageApiV1AdminGeoLanguagesCodeDeleteApiResponse,
        DeleteLanguageApiV1AdminGeoLanguagesCodeDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/languages/${queryArg.code}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      createSubdivisionApiV1AdminGeoSubdivisionsPost: build.mutation<
        CreateSubdivisionApiV1AdminGeoSubdivisionsPostApiResponse,
        CreateSubdivisionApiV1AdminGeoSubdivisionsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivisions`,
          method: 'POST',
          body: queryArg.createSubdivisionRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateSubdivisionApiV1AdminGeoSubdivisionsCodePatch: build.mutation<
        UpdateSubdivisionApiV1AdminGeoSubdivisionsCodePatchApiResponse,
        UpdateSubdivisionApiV1AdminGeoSubdivisionsCodePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivisions/${queryArg.code}`,
          method: 'PATCH',
          body: queryArg.updateSubdivisionRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteSubdivisionApiV1AdminGeoSubdivisionsCodeDelete: build.mutation<
        DeleteSubdivisionApiV1AdminGeoSubdivisionsCodeDeleteApiResponse,
        DeleteSubdivisionApiV1AdminGeoSubdivisionsCodeDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivisions/${queryArg.code}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPut: build.mutation<
        UpsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPutApiResponse,
        UpsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivisions/${queryArg.code}/translations`,
          method: 'PUT',
          body: queryArg.upsertSubdivisionTranslationsRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      listSubdivisionTypesApiV1AdminGeoSubdivisionTypesGet: build.query<
        ListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetApiResponse,
        ListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivision-types`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Geo'],
      }),
      createSubdivisionTypeApiV1AdminGeoSubdivisionTypesPost: build.mutation<
        CreateSubdivisionTypeApiV1AdminGeoSubdivisionTypesPostApiResponse,
        CreateSubdivisionTypeApiV1AdminGeoSubdivisionTypesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivision-types`,
          method: 'POST',
          body: queryArg.createSubdivisionTypeRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatch: build.mutation<
        UpdateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatchApiResponse,
        UpdateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivision-types/${queryArg.code}`,
          method: 'PATCH',
          body: queryArg.updateSubdivisionTypeRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDelete: build.mutation<
        DeleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDeleteApiResponse,
        DeleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/subdivision-types/${queryArg.code}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPut:
        build.mutation<
          UpsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPutApiResponse,
          UpsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPutApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/geo/subdivision-types/${queryArg.code}/translations`,
            method: 'PUT',
            body: queryArg.upsertSubdivisionTypeTranslationsRequest,
          }),
          invalidatesTags: ['Admin / Geo'],
        }),
      createDistrictApiV1AdminGeoDistrictsPost: build.mutation<
        CreateDistrictApiV1AdminGeoDistrictsPostApiResponse,
        CreateDistrictApiV1AdminGeoDistrictsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/districts`,
          method: 'POST',
          body: queryArg.createDistrictRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateDistrictApiV1AdminGeoDistrictsDistrictIdPatch: build.mutation<
        UpdateDistrictApiV1AdminGeoDistrictsDistrictIdPatchApiResponse,
        UpdateDistrictApiV1AdminGeoDistrictsDistrictIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/districts/${queryArg.districtId}`,
          method: 'PATCH',
          body: queryArg.updateDistrictRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteDistrictApiV1AdminGeoDistrictsDistrictIdDelete: build.mutation<
        DeleteDistrictApiV1AdminGeoDistrictsDistrictIdDeleteApiResponse,
        DeleteDistrictApiV1AdminGeoDistrictsDistrictIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/districts/${queryArg.districtId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPut: build.mutation<
        UpsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPutApiResponse,
        UpsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/districts/${queryArg.districtId}/translations`,
          method: 'PUT',
          body: queryArg.upsertDistrictTranslationsRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      listDistrictTypesApiV1AdminGeoDistrictTypesGet: build.query<
        ListDistrictTypesApiV1AdminGeoDistrictTypesGetApiResponse,
        ListDistrictTypesApiV1AdminGeoDistrictTypesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/district-types`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Geo'],
      }),
      createDistrictTypeApiV1AdminGeoDistrictTypesPost: build.mutation<
        CreateDistrictTypeApiV1AdminGeoDistrictTypesPostApiResponse,
        CreateDistrictTypeApiV1AdminGeoDistrictTypesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/district-types`,
          method: 'POST',
          body: queryArg.createDistrictTypeRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      updateDistrictTypeApiV1AdminGeoDistrictTypesCodePatch: build.mutation<
        UpdateDistrictTypeApiV1AdminGeoDistrictTypesCodePatchApiResponse,
        UpdateDistrictTypeApiV1AdminGeoDistrictTypesCodePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/district-types/${queryArg.code}`,
          method: 'PATCH',
          body: queryArg.updateDistrictTypeRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      deleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDelete: build.mutation<
        DeleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDeleteApiResponse,
        DeleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/district-types/${queryArg.code}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      upsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPut: build.mutation<
        UpsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPutApiResponse,
        UpsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/geo/district-types/${queryArg.code}/translations`,
          method: 'PUT',
          body: queryArg.upsertDistrictTypeTranslationsRequest,
        }),
        invalidatesTags: ['Admin / Geo'],
      }),
      registerApiV1AuthRegisterPost: build.mutation<
        RegisterApiV1AuthRegisterPostApiResponse,
        RegisterApiV1AuthRegisterPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/auth/register`,
          method: 'POST',
          body: queryArg.registerRequest,
        }),
        invalidatesTags: ['Authentication'],
      }),
      loginApiV1AuthLoginPost: build.mutation<
        LoginApiV1AuthLoginPostApiResponse,
        LoginApiV1AuthLoginPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/auth/login`,
          method: 'POST',
          body: queryArg.loginRequest,
        }),
        invalidatesTags: ['Authentication'],
      }),
      loginTelegramApiV1AuthTelegramPost: build.mutation<
        LoginTelegramApiV1AuthTelegramPostApiResponse,
        LoginTelegramApiV1AuthTelegramPostApiArg
      >({
        query: () => ({ url: `/api/v1/auth/telegram`, method: 'POST' }),
        invalidatesTags: ['Authentication'],
      }),
      refreshTokenApiV1AuthRefreshPost: build.mutation<
        RefreshTokenApiV1AuthRefreshPostApiResponse,
        RefreshTokenApiV1AuthRefreshPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/auth/refresh`,
          method: 'POST',
          body: queryArg.refreshTokenRequest,
        }),
        invalidatesTags: ['Authentication'],
      }),
      logoutApiV1AuthLogoutPost: build.mutation<
        LogoutApiV1AuthLogoutPostApiResponse,
        LogoutApiV1AuthLogoutPostApiArg
      >({
        query: () => ({ url: `/api/v1/auth/logout`, method: 'POST' }),
        invalidatesTags: ['Authentication'],
      }),
      logoutAllApiV1AuthLogoutAllPost: build.mutation<
        LogoutAllApiV1AuthLogoutAllPostApiResponse,
        LogoutAllApiV1AuthLogoutAllPostApiArg
      >({
        query: () => ({ url: `/api/v1/auth/logout/all`, method: 'POST' }),
        invalidatesTags: ['Authentication'],
      }),
      validateInvitationApiV1InvitationsTokenValidateGet: build.query<
        ValidateInvitationApiV1InvitationsTokenValidateGetApiResponse,
        ValidateInvitationApiV1InvitationsTokenValidateGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/invitations/${queryArg.token}/validate`,
        }),
        providesTags: ['Invitations'],
      }),
      acceptInvitationApiV1InvitationsTokenAcceptPost: build.mutation<
        AcceptInvitationApiV1InvitationsTokenAcceptPostApiResponse,
        AcceptInvitationApiV1InvitationsTokenAcceptPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/invitations/${queryArg.token}/accept`,
          method: 'POST',
          body: queryArg.acceptInvitationRequest,
        }),
        invalidatesTags: ['Invitations'],
      }),
      getMyProfileApiV1ProfileMeGet: build.query<
        GetMyProfileApiV1ProfileMeGetApiResponse,
        GetMyProfileApiV1ProfileMeGetApiArg
      >({
        query: () => ({ url: `/api/v1/profile/me` }),
        providesTags: ['Profile'],
      }),
      deleteMyAccountApiV1ProfileMeDelete: build.mutation<
        DeleteMyAccountApiV1ProfileMeDeleteApiResponse,
        DeleteMyAccountApiV1ProfileMeDeleteApiArg
      >({
        query: () => ({ url: `/api/v1/profile/me`, method: 'DELETE' }),
        invalidatesTags: ['Profile / Account'],
      }),
      updateProfileApiV1ProfileMePatch: build.mutation<
        UpdateProfileApiV1ProfileMePatchApiResponse,
        UpdateProfileApiV1ProfileMePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/profile/me`,
          method: 'PATCH',
          body: queryArg.updateProfileRequest,
        }),
        invalidatesTags: ['Profile'],
      }),
      changePasswordApiV1ProfilePasswordPut: build.mutation<
        ChangePasswordApiV1ProfilePasswordPutApiResponse,
        ChangePasswordApiV1ProfilePasswordPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/profile/password`,
          method: 'PUT',
          body: queryArg.changePasswordRequest,
        }),
        invalidatesTags: ['Profile / Account'],
      }),
      getMySessionsApiV1ProfileSessionsGet: build.query<
        GetMySessionsApiV1ProfileSessionsGetApiResponse,
        GetMySessionsApiV1ProfileSessionsGetApiArg
      >({
        query: () => ({ url: `/api/v1/profile/sessions` }),
        providesTags: ['Profile / Account'],
      }),
      listIdentitiesApiV1AdminIdentitiesGet: build.query<
        ListIdentitiesApiV1AdminIdentitiesGetApiResponse,
        ListIdentitiesApiV1AdminIdentitiesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            search: queryArg.search,
            roleId: queryArg.roleId,
            isActive: queryArg.isActive,
            sortBy: queryArg.sortBy,
            sortOrder: queryArg.sortOrder,
          },
        }),
        providesTags: ['Admin / IAM'],
      }),
      getIdentityDetailApiV1AdminIdentitiesIdentityIdGet: build.query<
        GetIdentityDetailApiV1AdminIdentitiesIdentityIdGetApiResponse,
        GetIdentityDetailApiV1AdminIdentitiesIdentityIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities/${queryArg.identityId}`,
        }),
        providesTags: ['Admin / IAM'],
      }),
      adminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePost: build.mutation<
        AdminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePostApiResponse,
        AdminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities/${queryArg.identityId}/deactivate`,
          method: 'POST',
          body: queryArg.adminDeactivateRequest,
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      adminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePost: build.mutation<
        AdminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePostApiResponse,
        AdminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities/${queryArg.identityId}/reactivate`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      listRolesApiV1AdminRolesGet: build.query<
        ListRolesApiV1AdminRolesGetApiResponse,
        ListRolesApiV1AdminRolesGetApiArg
      >({
        query: () => ({ url: `/api/v1/admin/roles` }),
        providesTags: ['Admin / IAM'],
      }),
      createRoleApiV1AdminRolesPost: build.mutation<
        CreateRoleApiV1AdminRolesPostApiResponse,
        CreateRoleApiV1AdminRolesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/roles`,
          method: 'POST',
          body: queryArg.createRoleRequest,
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      getRoleDetailApiV1AdminRolesRoleIdGet: build.query<
        GetRoleDetailApiV1AdminRolesRoleIdGetApiResponse,
        GetRoleDetailApiV1AdminRolesRoleIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/roles/${queryArg.roleId}`,
        }),
        providesTags: ['Admin / IAM'],
      }),
      updateRoleApiV1AdminRolesRoleIdPatch: build.mutation<
        UpdateRoleApiV1AdminRolesRoleIdPatchApiResponse,
        UpdateRoleApiV1AdminRolesRoleIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/roles/${queryArg.roleId}`,
          method: 'PATCH',
          body: queryArg.updateRoleRequest,
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      deleteRoleApiV1AdminRolesRoleIdDelete: build.mutation<
        DeleteRoleApiV1AdminRolesRoleIdDeleteApiResponse,
        DeleteRoleApiV1AdminRolesRoleIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/roles/${queryArg.roleId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      setRolePermissionsApiV1AdminRolesRoleIdPermissionsPut: build.mutation<
        SetRolePermissionsApiV1AdminRolesRoleIdPermissionsPutApiResponse,
        SetRolePermissionsApiV1AdminRolesRoleIdPermissionsPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/roles/${queryArg.roleId}/permissions`,
          method: 'PUT',
          body: queryArg.setRolePermissionsRequest,
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      listPermissionsApiV1AdminPermissionsGet: build.query<
        ListPermissionsApiV1AdminPermissionsGetApiResponse,
        ListPermissionsApiV1AdminPermissionsGetApiArg
      >({
        query: () => ({ url: `/api/v1/admin/permissions` }),
        providesTags: ['Admin / IAM'],
      }),
      assignRoleApiV1AdminIdentitiesIdentityIdRolesPost: build.mutation<
        AssignRoleApiV1AdminIdentitiesIdentityIdRolesPostApiResponse,
        AssignRoleApiV1AdminIdentitiesIdentityIdRolesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities/${queryArg.identityId}/roles`,
          method: 'POST',
          body: queryArg.assignRoleRequest,
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      revokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDelete: build.mutation<
        RevokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDeleteApiResponse,
        RevokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/identities/${queryArg.identityId}/roles/${queryArg.roleId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / IAM'],
      }),
      listStaffApiV1AdminStaffGet: build.query<
        ListStaffApiV1AdminStaffGetApiResponse,
        ListStaffApiV1AdminStaffGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            search: queryArg.search,
            roleId: queryArg.roleId,
            isActive: queryArg.isActive,
            sortBy: queryArg.sortBy,
            sortOrder: queryArg.sortOrder,
          },
        }),
        providesTags: ['Admin / Staff'],
      }),
      inviteStaffApiV1AdminStaffInvitationsPost: build.mutation<
        InviteStaffApiV1AdminStaffInvitationsPostApiResponse,
        InviteStaffApiV1AdminStaffInvitationsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/invitations`,
          method: 'POST',
          body: queryArg.inviteStaffRequest,
        }),
        invalidatesTags: ['Admin / Staff'],
      }),
      listInvitationsApiV1AdminStaffInvitationsGet: build.query<
        ListInvitationsApiV1AdminStaffInvitationsGetApiResponse,
        ListInvitationsApiV1AdminStaffInvitationsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/invitations`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            status: queryArg.status,
          },
        }),
        providesTags: ['Admin / Staff'],
      }),
      revokeInvitationApiV1AdminStaffInvitationsInvitationIdDelete: build.mutation<
        RevokeInvitationApiV1AdminStaffInvitationsInvitationIdDeleteApiResponse,
        RevokeInvitationApiV1AdminStaffInvitationsInvitationIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/invitations/${queryArg.invitationId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Staff'],
      }),
      getStaffDetailApiV1AdminStaffIdentityIdGet: build.query<
        GetStaffDetailApiV1AdminStaffIdentityIdGetApiResponse,
        GetStaffDetailApiV1AdminStaffIdentityIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/${queryArg.identityId}`,
        }),
        providesTags: ['Admin / Staff'],
      }),
      deactivateStaffApiV1AdminStaffIdentityIdDeactivatePost: build.mutation<
        DeactivateStaffApiV1AdminStaffIdentityIdDeactivatePostApiResponse,
        DeactivateStaffApiV1AdminStaffIdentityIdDeactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/${queryArg.identityId}/deactivate`,
          method: 'POST',
          body: queryArg.adminDeactivateRequest,
        }),
        invalidatesTags: ['Admin / Staff'],
      }),
      reactivateStaffApiV1AdminStaffIdentityIdReactivatePost: build.mutation<
        ReactivateStaffApiV1AdminStaffIdentityIdReactivatePostApiResponse,
        ReactivateStaffApiV1AdminStaffIdentityIdReactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/staff/${queryArg.identityId}/reactivate`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Staff'],
      }),
      listCustomersApiV1AdminCustomersGet: build.query<
        ListCustomersApiV1AdminCustomersGetApiResponse,
        ListCustomersApiV1AdminCustomersGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/customers`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            search: queryArg.search,
            isActive: queryArg.isActive,
            sortBy: queryArg.sortBy,
            sortOrder: queryArg.sortOrder,
          },
        }),
        providesTags: ['Admin / Customers'],
      }),
      getCustomerDetailApiV1AdminCustomersIdentityIdGet: build.query<
        GetCustomerDetailApiV1AdminCustomersIdentityIdGetApiResponse,
        GetCustomerDetailApiV1AdminCustomersIdentityIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/customers/${queryArg.identityId}`,
        }),
        providesTags: ['Admin / Customers'],
      }),
      deactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePost: build.mutation<
        DeactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePostApiResponse,
        DeactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/customers/${queryArg.identityId}/deactivate`,
          method: 'POST',
          body: queryArg.adminDeactivateRequest,
        }),
        invalidatesTags: ['Admin / Customers'],
      }),
      reactivateCustomerApiV1AdminCustomersIdentityIdReactivatePost: build.mutation<
        ReactivateCustomerApiV1AdminCustomersIdentityIdReactivatePostApiResponse,
        ReactivateCustomerApiV1AdminCustomersIdentityIdReactivatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/customers/${queryArg.identityId}/reactivate`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Customers'],
      }),
      createSupplierApiV1AdminSuppliersPost: build.mutation<
        CreateSupplierApiV1AdminSuppliersPostApiResponse,
        CreateSupplierApiV1AdminSuppliersPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers`,
          method: 'POST',
          body: queryArg.supplierCreateRequest,
        }),
        invalidatesTags: ['Admin / Suppliers'],
      }),
      listSuppliersApiV1AdminSuppliersGet: build.query<
        ListSuppliersApiV1AdminSuppliersGetApiResponse,
        ListSuppliersApiV1AdminSuppliersGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Suppliers'],
      }),
      getSupplierApiV1AdminSuppliersSupplierIdGet: build.query<
        GetSupplierApiV1AdminSuppliersSupplierIdGetApiResponse,
        GetSupplierApiV1AdminSuppliersSupplierIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers/${queryArg.supplierId}`,
        }),
        providesTags: ['Admin / Suppliers'],
      }),
      updateSupplierApiV1AdminSuppliersSupplierIdPut: build.mutation<
        UpdateSupplierApiV1AdminSuppliersSupplierIdPutApiResponse,
        UpdateSupplierApiV1AdminSuppliersSupplierIdPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers/${queryArg.supplierId}`,
          method: 'PUT',
          body: queryArg.supplierUpdateRequest,
        }),
        invalidatesTags: ['Admin / Suppliers'],
      }),
      deactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatch: build.mutation<
        DeactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatchApiResponse,
        DeactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers/${queryArg.supplierId}/deactivate`,
          method: 'PATCH',
        }),
        invalidatesTags: ['Admin / Suppliers'],
      }),
      activateSupplierApiV1AdminSuppliersSupplierIdActivatePatch: build.mutation<
        ActivateSupplierApiV1AdminSuppliersSupplierIdActivatePatchApiResponse,
        ActivateSupplierApiV1AdminSuppliersSupplierIdActivatePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/suppliers/${queryArg.supplierId}/activate`,
          method: 'PATCH',
        }),
        invalidatesTags: ['Admin / Suppliers'],
      }),
      getFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGet: build.query<
        GetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetApiResponse,
        GetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories/${queryArg.categoryId}/filters`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Categories'],
      }),
      getCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGet: build.query<
        GetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetApiResponse,
        GetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories/${queryArg.categoryId}/card-attributes`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Categories'],
      }),
      getComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGet:
        build.query<
          GetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetApiResponse,
          GetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/storefront/categories/${queryArg.categoryId}/comparison-attributes`,
            params: {
              lang: queryArg.lang,
            },
          }),
          providesTags: ['Storefront / Categories'],
        }),
      getFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGet: build.query<
        GetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetApiResponse,
        GetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories/${queryArg.categoryId}/form-attributes`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Categories'],
      }),
      storefrontCategoryTreeApiV1StorefrontCategoriesTreeGet: build.query<
        StorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetApiResponse,
        StorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories/tree`,
          params: {
            maxDepth: queryArg.maxDepth,
          },
        }),
        providesTags: ['Storefront / Taxonomy'],
      }),
      storefrontListCategoriesApiV1StorefrontCategoriesGet: build.query<
        StorefrontListCategoriesApiV1StorefrontCategoriesGetApiResponse,
        StorefrontListCategoriesApiV1StorefrontCategoriesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Storefront / Taxonomy'],
      }),
      storefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGet: build.query<
        StorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetApiResponse,
        StorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/categories/${queryArg.categoryId}`,
        }),
        providesTags: ['Storefront / Taxonomy'],
      }),
      storefrontListBrandsApiV1StorefrontBrandsGet: build.query<
        StorefrontListBrandsApiV1StorefrontBrandsGetApiResponse,
        StorefrontListBrandsApiV1StorefrontBrandsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/brands`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Storefront / Taxonomy'],
      }),
      storefrontGetBrandApiV1StorefrontBrandsBrandIdGet: build.query<
        StorefrontGetBrandApiV1StorefrontBrandsBrandIdGetApiResponse,
        StorefrontGetBrandApiV1StorefrontBrandsBrandIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/brands/${queryArg.brandId}`,
        }),
        providesTags: ['Storefront / Taxonomy'],
      }),
      listStorefrontProductsApiV1StorefrontProductsGet: build.query<
        ListStorefrontProductsApiV1StorefrontProductsGetApiResponse,
        ListStorefrontProductsApiV1StorefrontProductsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/products`,
          params: {
            categoryId: queryArg.categoryId,
            brandId: queryArg.brandId,
            priceMin: queryArg.priceMin,
            priceMax: queryArg.priceMax,
            inStock: queryArg.inStock,
            sort: queryArg.sort,
            limit: queryArg.limit,
            cursor: queryArg.cursor,
            includeTotal: queryArg.includeTotal,
            includeFacets: queryArg.includeFacets,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Products'],
      }),
      getStorefrontProductApiV1StorefrontProductsSlugGet: build.query<
        GetStorefrontProductApiV1StorefrontProductsSlugGetApiResponse,
        GetStorefrontProductApiV1StorefrontProductsSlugGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/products/${queryArg.slug}`,
          params: {
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Products'],
      }),
      getSimilarProductsApiV1StorefrontProductsSlugSimilarGet: build.query<
        GetSimilarProductsApiV1StorefrontProductsSlugSimilarGetApiResponse,
        GetSimilarProductsApiV1StorefrontProductsSlugSimilarGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/products/${queryArg.slug}/similar`,
          params: {
            limit: queryArg.limit,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Products'],
      }),
      getAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGet: build.query<
        GetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetApiResponse,
        GetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/products/${queryArg.slug}/also-viewed`,
          params: {
            limit: queryArg.limit,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Products'],
      }),
      searchProductsApiV1StorefrontSearchGet: build.query<
        SearchProductsApiV1StorefrontSearchGetApiResponse,
        SearchProductsApiV1StorefrontSearchGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/search`,
          params: {
            q: queryArg.q,
            categoryId: queryArg.categoryId,
            brandId: queryArg.brandId,
            priceMin: queryArg.priceMin,
            priceMax: queryArg.priceMax,
            inStock: queryArg.inStock,
            sort: queryArg.sort,
            limit: queryArg.limit,
            cursor: queryArg.cursor,
            includeTotal: queryArg.includeTotal,
            includeFacets: queryArg.includeFacets,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Search'],
      }),
      searchSuggestApiV1StorefrontSearchSuggestGet: build.query<
        SearchSuggestApiV1StorefrontSearchSuggestGetApiResponse,
        SearchSuggestApiV1StorefrontSearchSuggestGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/search/suggest`,
          params: {
            q: queryArg.q,
            limit: queryArg.limit,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Search'],
      }),
      listTrendingProductsApiV1StorefrontTrendingGet: build.query<
        ListTrendingProductsApiV1StorefrontTrendingGetApiResponse,
        ListTrendingProductsApiV1StorefrontTrendingGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/trending`,
          params: {
            limit: queryArg.limit,
            window: queryArg.window,
            categoryId: queryArg.categoryId,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / Trending'],
      }),
      getForYouFeedApiV1StorefrontForYouGet: build.query<
        GetForYouFeedApiV1StorefrontForYouGetApiResponse,
        GetForYouFeedApiV1StorefrontForYouGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/for-you`,
          params: {
            limit: queryArg.limit,
            cursor: queryArg.cursor,
            lang: queryArg.lang,
          },
        }),
        providesTags: ['Storefront / For You'],
      }),
      createBrandApiV1AdminCatalogBrandsPost: build.mutation<
        CreateBrandApiV1AdminCatalogBrandsPostApiResponse,
        CreateBrandApiV1AdminCatalogBrandsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands`,
          method: 'POST',
          body: queryArg.brandCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Brands'],
      }),
      listBrandsApiV1AdminCatalogBrandsGet: build.query<
        ListBrandsApiV1AdminCatalogBrandsGetApiResponse,
        ListBrandsApiV1AdminCatalogBrandsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Brands'],
      }),
      bulkCreateBrandsApiV1AdminCatalogBrandsBulkPost: build.mutation<
        BulkCreateBrandsApiV1AdminCatalogBrandsBulkPostApiResponse,
        BulkCreateBrandsApiV1AdminCatalogBrandsBulkPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands/bulk`,
          method: 'POST',
          body: queryArg.bulkCreateBrandsRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Brands'],
      }),
      getBrandApiV1AdminCatalogBrandsBrandIdGet: build.query<
        GetBrandApiV1AdminCatalogBrandsBrandIdGetApiResponse,
        GetBrandApiV1AdminCatalogBrandsBrandIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands/${queryArg.brandId}`,
        }),
        providesTags: ['Admin / Catalog / Brands'],
      }),
      updateBrandApiV1AdminCatalogBrandsBrandIdPatch: build.mutation<
        UpdateBrandApiV1AdminCatalogBrandsBrandIdPatchApiResponse,
        UpdateBrandApiV1AdminCatalogBrandsBrandIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands/${queryArg.brandId}`,
          method: 'PATCH',
          body: queryArg.brandUpdateRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Admin / Catalog / Brands'],
      }),
      deleteBrandApiV1AdminCatalogBrandsBrandIdDelete: build.mutation<
        DeleteBrandApiV1AdminCatalogBrandsBrandIdDeleteApiResponse,
        DeleteBrandApiV1AdminCatalogBrandsBrandIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/brands/${queryArg.brandId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Brands'],
      }),
      createCategoryApiV1AdminCatalogCategoriesPost: build.mutation<
        CreateCategoryApiV1AdminCatalogCategoriesPostApiResponse,
        CreateCategoryApiV1AdminCatalogCategoriesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories`,
          method: 'POST',
          body: queryArg.categoryCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Categories'],
      }),
      listCategoriesApiV1AdminCatalogCategoriesGet: build.query<
        ListCategoriesApiV1AdminCatalogCategoriesGetApiResponse,
        ListCategoriesApiV1AdminCatalogCategoriesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Categories'],
      }),
      bulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPost: build.mutation<
        BulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPostApiResponse,
        BulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories/bulk`,
          method: 'POST',
          body: queryArg.bulkCreateCategoriesRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Categories'],
      }),
      getCategoryTreeApiV1AdminCatalogCategoriesTreeGet: build.query<
        GetCategoryTreeApiV1AdminCatalogCategoriesTreeGetApiResponse,
        GetCategoryTreeApiV1AdminCatalogCategoriesTreeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories/tree`,
          params: {
            maxDepth: queryArg.maxDepth,
          },
        }),
        providesTags: ['Admin / Catalog / Categories'],
      }),
      getCategoryApiV1AdminCatalogCategoriesCategoryIdGet: build.query<
        GetCategoryApiV1AdminCatalogCategoriesCategoryIdGetApiResponse,
        GetCategoryApiV1AdminCatalogCategoriesCategoryIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories/${queryArg.categoryId}`,
        }),
        providesTags: ['Admin / Catalog / Categories'],
      }),
      updateCategoryApiV1AdminCatalogCategoriesCategoryIdPatch: build.mutation<
        UpdateCategoryApiV1AdminCatalogCategoriesCategoryIdPatchApiResponse,
        UpdateCategoryApiV1AdminCatalogCategoriesCategoryIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories/${queryArg.categoryId}`,
          method: 'PATCH',
          body: queryArg.categoryUpdateRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Admin / Catalog / Categories'],
      }),
      deleteCategoryApiV1AdminCatalogCategoriesCategoryIdDelete: build.mutation<
        DeleteCategoryApiV1AdminCatalogCategoriesCategoryIdDeleteApiResponse,
        DeleteCategoryApiV1AdminCatalogCategoriesCategoryIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/categories/${queryArg.categoryId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Categories'],
      }),
      createAttributeApiV1AdminCatalogAttributesPost: build.mutation<
        CreateAttributeApiV1AdminCatalogAttributesPostApiResponse,
        CreateAttributeApiV1AdminCatalogAttributesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes`,
          method: 'POST',
          body: queryArg.attributeCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attributes'],
      }),
      listAttributesApiV1AdminCatalogAttributesGet: build.query<
        ListAttributesApiV1AdminCatalogAttributesGetApiResponse,
        ListAttributesApiV1AdminCatalogAttributesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            dataType: queryArg.dataType,
            uiType: queryArg.uiType,
            isDictionary: queryArg.isDictionary,
            groupId: queryArg.groupId,
            level: queryArg.level,
            isFilterable: queryArg.isFilterable,
            isSearchable: queryArg.isSearchable,
            isComparable: queryArg.isComparable,
            search: queryArg.search,
          },
        }),
        providesTags: ['Admin / Catalog / Attributes'],
      }),
      bulkCreateAttributesApiV1AdminCatalogAttributesBulkPost: build.mutation<
        BulkCreateAttributesApiV1AdminCatalogAttributesBulkPostApiResponse,
        BulkCreateAttributesApiV1AdminCatalogAttributesBulkPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/bulk`,
          method: 'POST',
          body: queryArg.bulkCreateAttributesRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attributes'],
      }),
      getAttributeApiV1AdminCatalogAttributesAttributeIdGet: build.query<
        GetAttributeApiV1AdminCatalogAttributesAttributeIdGetApiResponse,
        GetAttributeApiV1AdminCatalogAttributesAttributeIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}`,
        }),
        providesTags: ['Admin / Catalog / Attributes'],
      }),
      updateAttributeApiV1AdminCatalogAttributesAttributeIdPatch: build.mutation<
        UpdateAttributeApiV1AdminCatalogAttributesAttributeIdPatchApiResponse,
        UpdateAttributeApiV1AdminCatalogAttributesAttributeIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}`,
          method: 'PATCH',
          body: queryArg.attributeUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attributes'],
      }),
      deleteAttributeApiV1AdminCatalogAttributesAttributeIdDelete: build.mutation<
        DeleteAttributeApiV1AdminCatalogAttributesAttributeIdDeleteApiResponse,
        DeleteAttributeApiV1AdminCatalogAttributesAttributeIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Attributes'],
      }),
      getAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGet: build.query<
        GetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetApiResponse,
        GetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/usage`,
        }),
        providesTags: ['Admin / Catalog / Attributes'],
      }),
      createAttributeGroupApiV1AdminCatalogAttributeGroupsPost: build.mutation<
        CreateAttributeGroupApiV1AdminCatalogAttributeGroupsPostApiResponse,
        CreateAttributeGroupApiV1AdminCatalogAttributeGroupsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-groups`,
          method: 'POST',
          body: queryArg.attributeGroupCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Groups'],
      }),
      listAttributeGroupsApiV1AdminCatalogAttributeGroupsGet: build.query<
        ListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetApiResponse,
        ListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-groups`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Attribute Groups'],
      }),
      getAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGet: build.query<
        GetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetApiResponse,
        GetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-groups/${queryArg.groupId}`,
        }),
        providesTags: ['Admin / Catalog / Attribute Groups'],
      }),
      updateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatch: build.mutation<
        UpdateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatchApiResponse,
        UpdateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-groups/${queryArg.groupId}`,
          method: 'PATCH',
          body: queryArg.attributeGroupUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Groups'],
      }),
      deleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDelete: build.mutation<
        DeleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDeleteApiResponse,
        DeleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-groups/${queryArg.groupId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Groups'],
      }),
      addAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPost: build.mutation<
        AddAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPostApiResponse,
        AddAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values`,
          method: 'POST',
          body: queryArg.attributeValueCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      listAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGet: build.query<
        ListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetApiResponse,
        ListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            search: queryArg.search,
          },
        }),
        providesTags: ['Admin / Catalog / Attribute Values'],
      }),
      bulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPost: build.mutation<
        BulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPostApiResponse,
        BulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/bulk`,
          method: 'POST',
          body: queryArg.bulkAddAttributeValuesRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      getAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGet: build.query<
        GetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetApiResponse,
        GetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/${queryArg.valueId}`,
        }),
        providesTags: ['Admin / Catalog / Attribute Values'],
      }),
      updateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatch: build.mutation<
        UpdateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatchApiResponse,
        UpdateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/${queryArg.valueId}`,
          method: 'PATCH',
          body: queryArg.attributeValueUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      deleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDelete: build.mutation<
        DeleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeleteApiResponse,
        DeleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/${queryArg.valueId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      deactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatch:
        build.mutation<
          DeactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatchApiResponse,
          DeactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatchApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/${queryArg.valueId}/deactivate`,
            method: 'PATCH',
          }),
          invalidatesTags: ['Admin / Catalog / Attribute Values'],
        }),
      activateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatch: build.mutation<
        ActivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatchApiResponse,
        ActivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/${queryArg.valueId}/activate`,
          method: 'PATCH',
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      reorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPost: build.mutation<
        ReorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPostApiResponse,
        ReorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attributes/${queryArg.attributeId}/values/reorder`,
          method: 'POST',
          body: queryArg.reorderAttributeValuesRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Values'],
      }),
      createTemplateApiV1AdminCatalogAttributeTemplatesPost: build.mutation<
        CreateTemplateApiV1AdminCatalogAttributeTemplatesPostApiResponse,
        CreateTemplateApiV1AdminCatalogAttributeTemplatesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates`,
          method: 'POST',
          body: queryArg.attributeTemplateCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      listTemplatesApiV1AdminCatalogAttributeTemplatesGet: build.query<
        ListTemplatesApiV1AdminCatalogAttributeTemplatesGetApiResponse,
        ListTemplatesApiV1AdminCatalogAttributeTemplatesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      cloneTemplateApiV1AdminCatalogAttributeTemplatesClonePost: build.mutation<
        CloneTemplateApiV1AdminCatalogAttributeTemplatesClonePostApiResponse,
        CloneTemplateApiV1AdminCatalogAttributeTemplatesClonePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/clone`,
          method: 'POST',
          body: queryArg.cloneAttributeTemplateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      getTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGet: build.query<
        GetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetApiResponse,
        GetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}`,
        }),
        providesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      updateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatch: build.mutation<
        UpdateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatchApiResponse,
        UpdateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}`,
          method: 'PATCH',
          body: queryArg.attributeTemplateUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      deleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDelete: build.mutation<
        DeleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDeleteApiResponse,
        DeleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      bindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPost: build.mutation<
        BindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPostApiResponse,
        BindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}/attributes`,
          method: 'POST',
          body: queryArg.templateAttributeBindingRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      listBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGet: build.query<
        ListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetApiResponse,
        ListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}/attributes`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Attribute Templates'],
      }),
      updateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatch:
        build.mutation<
          UpdateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatchApiResponse,
          UpdateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatchApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}/attributes/${queryArg.bindingId}`,
            method: 'PATCH',
            body: queryArg.templateAttributeBindingUpdateRequest,
          }),
          invalidatesTags: ['Admin / Catalog / Attribute Templates'],
        }),
      unbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDelete:
        build.mutation<
          UnbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDeleteApiResponse,
          UnbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDeleteApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}/attributes/${queryArg.bindingId}`,
            method: 'DELETE',
          }),
          invalidatesTags: ['Admin / Catalog / Attribute Templates'],
        }),
      reorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPost:
        build.mutation<
          ReorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPostApiResponse,
          ReorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/attribute-templates/${queryArg.templateId}/attributes/reorder`,
            method: 'POST',
            body: queryArg.templateBindingReorderRequest,
          }),
          invalidatesTags: ['Admin / Catalog / Attribute Templates'],
        }),
      createProductApiV1AdminCatalogProductsPost: build.mutation<
        CreateProductApiV1AdminCatalogProductsPostApiResponse,
        CreateProductApiV1AdminCatalogProductsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products`,
          method: 'POST',
          body: queryArg.productCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      listProductsApiV1AdminCatalogProductsGet: build.query<
        ListProductsApiV1AdminCatalogProductsGetApiResponse,
        ListProductsApiV1AdminCatalogProductsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
            status: queryArg.status,
            brandId: queryArg.brandId,
            sortBy: queryArg.sortBy,
            publishedAfter: queryArg.publishedAfter,
          },
        }),
        providesTags: ['Admin / Catalog / Products'],
      }),
      getProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGet: build.query<
        GetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetApiResponse,
        GetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/completeness`,
        }),
        providesTags: ['Admin / Catalog / Products'],
      }),
      getProductApiV1AdminCatalogProductsProductIdGet: build.query<
        GetProductApiV1AdminCatalogProductsProductIdGetApiResponse,
        GetProductApiV1AdminCatalogProductsProductIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}`,
        }),
        providesTags: ['Admin / Catalog / Products'],
      }),
      updateProductApiV1AdminCatalogProductsProductIdPatch: build.mutation<
        UpdateProductApiV1AdminCatalogProductsProductIdPatchApiResponse,
        UpdateProductApiV1AdminCatalogProductsProductIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}`,
          method: 'PATCH',
          body: queryArg.productUpdateRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      deleteProductApiV1AdminCatalogProductsProductIdDelete: build.mutation<
        DeleteProductApiV1AdminCatalogProductsProductIdDeleteApiResponse,
        DeleteProductApiV1AdminCatalogProductsProductIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      streamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGet: build.query<
        StreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetApiResponse,
        StreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/skus/pricing-events`,
        }),
        providesTags: ['Admin / Catalog / Products'],
      }),
      bulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePost:
        build.mutation<
          BulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePostApiResponse,
          BulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/products/${queryArg.productId}/skus/bulk-purchase-price`,
            method: 'POST',
            body: queryArg.bulkPurchasePriceRequest,
          }),
          invalidatesTags: ['Admin / Catalog / Products'],
        }),
      changeProductStatusApiV1AdminCatalogProductsProductIdStatusPatch: build.mutation<
        ChangeProductStatusApiV1AdminCatalogProductsProductIdStatusPatchApiResponse,
        ChangeProductStatusApiV1AdminCatalogProductsProductIdStatusPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/status`,
          method: 'PATCH',
          body: queryArg.productStatusChangeRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      validateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePost: build.mutation<
        ValidateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePostApiResponse,
        ValidateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/_validate-update`,
          method: 'POST',
          body: queryArg.productUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      validateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPost: build.mutation<
        ValidateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPostApiResponse,
        ValidateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/_validate-publish`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Catalog / Products'],
      }),
      addVariantApiV1AdminCatalogProductsProductIdVariantsPost: build.mutation<
        AddVariantApiV1AdminCatalogProductsProductIdVariantsPostApiResponse,
        AddVariantApiV1AdminCatalogProductsProductIdVariantsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants`,
          method: 'POST',
          body: queryArg.productVariantCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Variants'],
      }),
      listVariantsApiV1AdminCatalogProductsProductIdVariantsGet: build.query<
        ListVariantsApiV1AdminCatalogProductsProductIdVariantsGetApiResponse,
        ListVariantsApiV1AdminCatalogProductsProductIdVariantsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants`,
          params: {
            limit: queryArg.limit,
            offset: queryArg.offset,
          },
        }),
        providesTags: ['Admin / Catalog / Variants'],
      }),
      updateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatch: build.mutation<
        UpdateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatchApiResponse,
        UpdateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}`,
          method: 'PATCH',
          body: queryArg.productVariantUpdateRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Admin / Catalog / Variants'],
      }),
      deleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDelete: build.mutation<
        DeleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDeleteApiResponse,
        DeleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Variants'],
      }),
      addSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPost: build.mutation<
        AddSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPostApiResponse,
        AddSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}/skus`,
          method: 'POST',
          body: queryArg.skuCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / SKUs'],
      }),
      listSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGet: build.query<
        ListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetApiResponse,
        ListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}/skus`,
          params: {
            limit: queryArg.limit,
            offset: queryArg.offset,
          },
        }),
        providesTags: ['Admin / Catalog / SKUs'],
      }),
      generateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePost:
        build.mutation<
          GenerateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePostApiResponse,
          GenerateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}/skus/generate`,
            method: 'POST',
            body: queryArg.skuMatrixGenerateRequest,
          }),
          invalidatesTags: ['Admin / Catalog / SKUs'],
        }),
      updateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatch: build.mutation<
        UpdateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatchApiResponse,
        UpdateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}/skus/${queryArg.skuId}`,
          method: 'PATCH',
          body: queryArg.skuUpdateRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Admin / Catalog / SKUs'],
      }),
      deleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDelete: build.mutation<
        DeleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDeleteApiResponse,
        DeleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/variants/${queryArg.variantId}/skus/${queryArg.skuId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / SKUs'],
      }),
      assignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPost: build.mutation<
        AssignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPostApiResponse,
        AssignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/attributes`,
          method: 'POST',
          body: queryArg.productAttributeAssignRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Product Attributes'],
      }),
      listProductAttributesApiV1AdminCatalogProductsProductIdAttributesGet: build.query<
        ListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetApiResponse,
        ListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/attributes`,
          params: {
            limit: queryArg.limit,
            offset: queryArg.offset,
          },
        }),
        providesTags: ['Admin / Catalog / Product Attributes'],
      }),
      bulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPost:
        build.mutation<
          BulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPostApiResponse,
          BulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/products/${queryArg.productId}/attributes/bulk`,
            method: 'POST',
            body: queryArg.bulkAssignProductAttributesRequest,
          }),
          invalidatesTags: ['Admin / Catalog / Product Attributes'],
        }),
      deleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDelete:
        build.mutation<
          DeleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDeleteApiResponse,
          DeleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDeleteApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/catalog/products/${queryArg.productId}/attributes/${queryArg.attributeId}`,
            method: 'DELETE',
          }),
          invalidatesTags: ['Admin / Catalog / Product Attributes'],
        }),
      addProductMediaApiV1AdminCatalogProductsProductIdMediaPost: build.mutation<
        AddProductMediaApiV1AdminCatalogProductsProductIdMediaPostApiResponse,
        AddProductMediaApiV1AdminCatalogProductsProductIdMediaPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/media`,
          method: 'POST',
          body: queryArg.mediaAssetCreateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Product Media'],
      }),
      listProductMediaApiV1AdminCatalogProductsProductIdMediaGet: build.query<
        ListProductMediaApiV1AdminCatalogProductsProductIdMediaGetApiResponse,
        ListProductMediaApiV1AdminCatalogProductsProductIdMediaGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/media`,
          params: {
            offset: queryArg.offset,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Catalog / Product Media'],
      }),
      updateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatch: build.mutation<
        UpdateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatchApiResponse,
        UpdateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/media/${queryArg.mediaId}`,
          method: 'PATCH',
          body: queryArg.mediaAssetUpdateRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Product Media'],
      }),
      deleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDelete: build.mutation<
        DeleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDeleteApiResponse,
        DeleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/media/${queryArg.mediaId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Catalog / Product Media'],
      }),
      reorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPost: build.mutation<
        ReorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPostApiResponse,
        ReorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/catalog/products/${queryArg.productId}/media/reorder`,
          method: 'POST',
          body: queryArg.mediaAssetReorderRequest,
        }),
        invalidatesTags: ['Admin / Catalog / Product Media'],
      }),
      listVariablesApiV1AdminPricingVariablesGet: build.query<
        ListVariablesApiV1AdminPricingVariablesGetApiResponse,
        ListVariablesApiV1AdminPricingVariablesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/variables`,
          params: {
            scope: queryArg.scope,
            isSystem: queryArg.isSystem,
            isFxRate: queryArg.isFxRate,
          },
        }),
        providesTags: ['Admin / Pricing / Variables'],
      }),
      createVariableApiV1AdminPricingVariablesPost: build.mutation<
        CreateVariableApiV1AdminPricingVariablesPostApiResponse,
        CreateVariableApiV1AdminPricingVariablesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/variables`,
          method: 'POST',
          body: queryArg.createVariableRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Variables'],
      }),
      getVariableApiV1AdminPricingVariablesVariableIdGet: build.query<
        GetVariableApiV1AdminPricingVariablesVariableIdGetApiResponse,
        GetVariableApiV1AdminPricingVariablesVariableIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/variables/${queryArg.variableId}`,
        }),
        providesTags: ['Admin / Pricing / Variables'],
      }),
      updateVariableApiV1AdminPricingVariablesVariableIdPatch: build.mutation<
        UpdateVariableApiV1AdminPricingVariablesVariableIdPatchApiResponse,
        UpdateVariableApiV1AdminPricingVariablesVariableIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/variables/${queryArg.variableId}`,
          method: 'PATCH',
          body: queryArg.updateVariableRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Variables'],
      }),
      deleteVariableApiV1AdminPricingVariablesVariableIdDelete: build.mutation<
        DeleteVariableApiV1AdminPricingVariablesVariableIdDeleteApiResponse,
        DeleteVariableApiV1AdminPricingVariablesVariableIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/variables/${queryArg.variableId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Pricing / Variables'],
      }),
      listContextsApiV1AdminPricingContextsGet: build.query<
        ListContextsApiV1AdminPricingContextsGetApiResponse,
        ListContextsApiV1AdminPricingContextsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts`,
          params: {
            isActive: queryArg.isActive,
            isFrozen: queryArg.isFrozen,
          },
        }),
        providesTags: ['Admin / Pricing / Contexts'],
      }),
      createContextApiV1AdminPricingContextsPost: build.mutation<
        CreateContextApiV1AdminPricingContextsPostApiResponse,
        CreateContextApiV1AdminPricingContextsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts`,
          method: 'POST',
          body: queryArg.createContextRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Contexts'],
      }),
      getContextApiV1AdminPricingContextsContextIdGet: build.query<
        GetContextApiV1AdminPricingContextsContextIdGetApiResponse,
        GetContextApiV1AdminPricingContextsContextIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}`,
        }),
        providesTags: ['Admin / Pricing / Contexts'],
      }),
      updateContextApiV1AdminPricingContextsContextIdPatch: build.mutation<
        UpdateContextApiV1AdminPricingContextsContextIdPatchApiResponse,
        UpdateContextApiV1AdminPricingContextsContextIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}`,
          method: 'PATCH',
          body: queryArg.updateContextRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Contexts'],
      }),
      deactivateContextApiV1AdminPricingContextsContextIdDelete: build.mutation<
        DeactivateContextApiV1AdminPricingContextsContextIdDeleteApiResponse,
        DeactivateContextApiV1AdminPricingContextsContextIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Pricing / Contexts'],
      }),
      freezeContextApiV1AdminPricingContextsContextIdFreezePost: build.mutation<
        FreezeContextApiV1AdminPricingContextsContextIdFreezePostApiResponse,
        FreezeContextApiV1AdminPricingContextsContextIdFreezePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/freeze`,
          method: 'POST',
          body: queryArg.freezeContextRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Contexts'],
      }),
      unfreezeContextApiV1AdminPricingContextsContextIdUnfreezePost: build.mutation<
        UnfreezeContextApiV1AdminPricingContextsContextIdUnfreezePostApiResponse,
        UnfreezeContextApiV1AdminPricingContextsContextIdUnfreezePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/unfreeze`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Contexts'],
      }),
      getContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGet: build.query<
        GetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetApiResponse,
        GetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/variables/values`,
        }),
        providesTags: ['Admin / Pricing / Contexts'],
      }),
      setContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePut:
        build.mutation<
          SetContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePutApiResponse,
          SetContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePutApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/variables/values/${queryArg.variableCode}`,
            method: 'PUT',
            body: queryArg.setContextGlobalValueRequest,
          }),
          invalidatesTags: ['Admin / Pricing / Contexts'],
        }),
      listVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGet: build.query<
        ListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetApiResponse,
        ListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/versions`,
          params: {
            status: queryArg.status,
          },
        }),
        providesTags: ['Admin / Pricing / Formulas'],
      }),
      getVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGet: build.query<
        GetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetApiResponse,
        GetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/versions/${queryArg.versionId}`,
        }),
        providesTags: ['Admin / Pricing / Formulas'],
      }),
      getDraftApiV1AdminPricingContextsContextIdFormulaDraftGet: build.query<
        GetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetApiResponse,
        GetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/draft`,
        }),
        providesTags: ['Admin / Pricing / Formulas'],
      }),
      upsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPut: build.mutation<
        UpsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPutApiResponse,
        UpsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/draft`,
          method: 'PUT',
          body: queryArg.upsertFormulaDraftRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Formulas'],
      }),
      discardDraftApiV1AdminPricingContextsContextIdFormulaDraftDelete: build.mutation<
        DiscardDraftApiV1AdminPricingContextsContextIdFormulaDraftDeleteApiResponse,
        DiscardDraftApiV1AdminPricingContextsContextIdFormulaDraftDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/draft`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Pricing / Formulas'],
      }),
      publishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPost: build.mutation<
        PublishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPostApiResponse,
        PublishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/draft/publish`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Formulas'],
      }),
      rollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPost:
        build.mutation<
          RollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPostApiResponse,
          RollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/contexts/${queryArg.contextId}/formula/versions/${queryArg.versionId}/rollback`,
            method: 'POST',
          }),
          invalidatesTags: ['Admin / Pricing / Formulas'],
        }),
      previewPriceApiV1AdminPricingPreviewPost: build.mutation<
        PreviewPriceApiV1AdminPricingPreviewPostApiResponse,
        PreviewPriceApiV1AdminPricingPreviewPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/preview`,
          method: 'POST',
          body: queryArg.previewPriceRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Preview'],
      }),
      previewSkuPricingApiV1AdminPricingPreviewSkuPost: build.mutation<
        PreviewSkuPricingApiV1AdminPricingPreviewSkuPostApiResponse,
        PreviewSkuPricingApiV1AdminPricingPreviewSkuPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/preview-sku`,
          method: 'POST',
          body: queryArg.previewSkuPricingRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Preview'],
      }),
      getProfileApiV1AdminPricingProductsProductIdProfileGet: build.query<
        GetProfileApiV1AdminPricingProductsProductIdProfileGetApiResponse,
        GetProfileApiV1AdminPricingProductsProductIdProfileGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/products/${queryArg.productId}/profile`,
        }),
        providesTags: ['Admin / Pricing / Products'],
      }),
      upsertProfileApiV1AdminPricingProductsProductIdProfilePut: build.mutation<
        UpsertProfileApiV1AdminPricingProductsProductIdProfilePutApiResponse,
        UpsertProfileApiV1AdminPricingProductsProductIdProfilePutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/products/${queryArg.productId}/profile`,
          method: 'PUT',
          body: queryArg.upsertProductPricingProfileRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Products'],
      }),
      deleteProfileApiV1AdminPricingProductsProductIdProfileDelete: build.mutation<
        DeleteProfileApiV1AdminPricingProductsProductIdProfileDeleteApiResponse,
        DeleteProfileApiV1AdminPricingProductsProductIdProfileDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/products/${queryArg.productId}/profile`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Pricing / Products'],
      }),
      getRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGet:
        build.query<
          GetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetApiResponse,
          GetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/products/${queryArg.productId}/profile/required-variables`,
          }),
          providesTags: ['Admin / Pricing / Products'],
        }),
      getSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGet: build.query<
        GetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetApiResponse,
        GetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/suppliers/${queryArg.supplierId}`,
        }),
        providesTags: ['Admin / Pricing / Suppliers'],
      }),
      upsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPut: build.mutation<
        UpsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPutApiResponse,
        UpsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/suppliers/${queryArg.supplierId}`,
          method: 'PUT',
          body: queryArg.upsertSupplierPricingSettingsRequest,
        }),
        invalidatesTags: ['Admin / Pricing / Suppliers'],
      }),
      listSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGet: build.query<
        ListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetApiResponse,
        ListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetApiArg
      >({
        query: () => ({ url: `/api/v1/admin/pricing/supplier-type-mapping` }),
        providesTags: ['Admin / Pricing / Supplier-Type Mapping'],
      }),
      getSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGet: build.query<
        GetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetApiResponse,
        GetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/supplier-type-mapping/${queryArg.supplierType}`,
        }),
        providesTags: ['Admin / Pricing / Supplier-Type Mapping'],
      }),
      upsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePut:
        build.mutation<
          UpsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePutApiResponse,
          UpsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePutApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/supplier-type-mapping/${queryArg.supplierType}`,
            method: 'PUT',
            body: queryArg.upsertSupplierTypeContextMappingRequest,
          }),
          invalidatesTags: ['Admin / Pricing / Supplier-Type Mapping'],
        }),
      deleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDelete:
        build.mutation<
          DeleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDeleteApiResponse,
          DeleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDeleteApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/supplier-type-mapping/${queryArg.supplierType}`,
            method: 'DELETE',
          }),
          invalidatesTags: ['Admin / Pricing / Supplier-Type Mapping'],
        }),
      getCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGet: build.query<
        GetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetApiResponse,
        GetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/categories/${queryArg.categoryId}`,
          params: {
            contextId: queryArg.contextId,
          },
        }),
        providesTags: ['Admin / Pricing / Categories'],
      }),
      upsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPut:
        build.mutation<
          UpsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPutApiResponse,
          UpsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPutApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/categories/${queryArg.categoryId}/${queryArg.contextId}`,
            method: 'PUT',
            body: queryArg.upsertCategoryPricingSettingsRequest,
          }),
          invalidatesTags: ['Admin / Pricing / Categories'],
        }),
      deleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDelete:
        build.mutation<
          DeleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDeleteApiResponse,
          DeleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDeleteApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/pricing/categories/${queryArg.categoryId}/${queryArg.contextId}`,
            method: 'DELETE',
          }),
          invalidatesTags: ['Admin / Pricing / Categories'],
        }),
      recomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPost: build.mutation<
        RecomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPostApiResponse,
        RecomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/recompute/skus/${queryArg.skuId}`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Recompute'],
      }),
      recomputeContextApiV1AdminPricingRecomputeContextsContextIdPost: build.mutation<
        RecomputeContextApiV1AdminPricingRecomputeContextsContextIdPostApiResponse,
        RecomputeContextApiV1AdminPricingRecomputeContextsContextIdPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/recompute/contexts/${queryArg.contextId}`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Recompute'],
      }),
      recomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPost: build.mutation<
        RecomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPostApiResponse,
        RecomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/recompute/categories/${queryArg.categoryId}`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Recompute'],
      }),
      recomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPost: build.mutation<
        RecomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPostApiResponse,
        RecomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/pricing/recompute/suppliers/${queryArg.supplierId}`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Pricing / Recompute'],
      }),
      getTrendingProductsApiV1AdminAnalyticsTrendingGet: build.query<
        GetTrendingProductsApiV1AdminAnalyticsTrendingGetApiResponse,
        GetTrendingProductsApiV1AdminAnalyticsTrendingGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/analytics/trending`,
          params: {
            limit: queryArg.limit,
            window: queryArg.window,
            categoryId: queryArg.categoryId,
          },
        }),
        providesTags: ['Admin / Analytics'],
      }),
      getSearchAnalyticsApiV1AdminAnalyticsSearchGet: build.query<
        GetSearchAnalyticsApiV1AdminAnalyticsSearchGetApiResponse,
        GetSearchAnalyticsApiV1AdminAnalyticsSearchGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/analytics/search`,
          params: {
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Admin / Analytics'],
      }),
      addItemApiV1CartItemsPost: build.mutation<
        AddItemApiV1CartItemsPostApiResponse,
        AddItemApiV1CartItemsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/items`,
          method: 'POST',
          body: queryArg.addItemRequest,
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        invalidatesTags: ['Cart'],
      }),
      removeItemApiV1CartItemsSkuIdDelete: build.mutation<
        RemoveItemApiV1CartItemsSkuIdDeleteApiResponse,
        RemoveItemApiV1CartItemsSkuIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/items/${queryArg.skuId}`,
          method: 'DELETE',
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        invalidatesTags: ['Cart'],
      }),
      updateQuantityApiV1CartItemsSkuIdPatch: build.mutation<
        UpdateQuantityApiV1CartItemsSkuIdPatchApiResponse,
        UpdateQuantityApiV1CartItemsSkuIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/items/${queryArg.skuId}`,
          method: 'PATCH',
          body: queryArg.updateQuantityRequest,
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        invalidatesTags: ['Cart'],
      }),
      clearCartApiV1CartDelete: build.mutation<
        ClearCartApiV1CartDeleteApiResponse,
        ClearCartApiV1CartDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart`,
          method: 'DELETE',
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        invalidatesTags: ['Cart'],
      }),
      getCartApiV1CartGet: build.query<GetCartApiV1CartGetApiResponse, GetCartApiV1CartGetApiArg>({
        query: (queryArg) => ({
          url: `/api/v1/cart`,
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        providesTags: ['Cart'],
      }),
      getCartSummaryApiV1CartSummaryGet: build.query<
        GetCartSummaryApiV1CartSummaryGetApiResponse,
        GetCartSummaryApiV1CartSummaryGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/summary`,
          headers: {
            'x-anonymous-token': queryArg['x-anonymous-token'],
          },
        }),
        providesTags: ['Cart'],
      }),
      initiateCheckoutApiV1CartCheckoutPost: build.mutation<
        InitiateCheckoutApiV1CartCheckoutPostApiResponse,
        InitiateCheckoutApiV1CartCheckoutPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/checkout`,
          method: 'POST',
          body: queryArg.initiateCheckoutRequest,
        }),
        invalidatesTags: ['Cart'],
      }),
      confirmCheckoutApiV1CartCheckoutConfirmPost: build.mutation<
        ConfirmCheckoutApiV1CartCheckoutConfirmPostApiResponse,
        ConfirmCheckoutApiV1CartCheckoutConfirmPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/checkout/confirm`,
          method: 'POST',
          body: queryArg.confirmCheckoutRequest,
        }),
        invalidatesTags: ['Cart'],
      }),
      cancelCheckoutApiV1CartCheckoutCancelPost: build.mutation<
        CancelCheckoutApiV1CartCheckoutCancelPostApiResponse,
        CancelCheckoutApiV1CartCheckoutCancelPostApiArg
      >({
        query: () => ({ url: `/api/v1/cart/checkout/cancel`, method: 'POST' }),
        invalidatesTags: ['Cart'],
      }),
      mergeCartsApiV1CartMergePost: build.mutation<
        MergeCartsApiV1CartMergePostApiResponse,
        MergeCartsApiV1CartMergePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/cart/merge`,
          method: 'POST',
          body: queryArg.mergeCartRequest,
        }),
        invalidatesTags: ['Cart'],
      }),
      createAnonymousTokenApiV1CartAnonymousTokenPost: build.mutation<
        CreateAnonymousTokenApiV1CartAnonymousTokenPostApiResponse,
        CreateAnonymousTokenApiV1CartAnonymousTokenPostApiArg
      >({
        query: () => ({ url: `/api/v1/cart/anonymous-token`, method: 'POST' }),
        invalidatesTags: ['Cart'],
      }),
      listFavoriteListsApiV1FavoritesListsGet: build.query<
        ListFavoriteListsApiV1FavoritesListsGetApiResponse,
        ListFavoriteListsApiV1FavoritesListsGetApiArg
      >({
        query: () => ({ url: `/api/v1/favorites/lists` }),
        providesTags: ['Favorites'],
      }),
      createFavoriteListApiV1FavoritesListsPost: build.mutation<
        CreateFavoriteListApiV1FavoritesListsPostApiResponse,
        CreateFavoriteListApiV1FavoritesListsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/lists`,
          method: 'POST',
          body: queryArg.createFavoriteListRequest,
        }),
        invalidatesTags: ['Favorites'],
      }),
      renameFavoriteListApiV1FavoritesListsListIdPatch: build.mutation<
        RenameFavoriteListApiV1FavoritesListsListIdPatchApiResponse,
        RenameFavoriteListApiV1FavoritesListsListIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/lists/${queryArg.listId}`,
          method: 'PATCH',
          body: queryArg.renameFavoriteListRequest,
        }),
        invalidatesTags: ['Favorites'],
      }),
      deleteFavoriteListApiV1FavoritesListsListIdDelete: build.mutation<
        DeleteFavoriteListApiV1FavoritesListsListIdDeleteApiResponse,
        DeleteFavoriteListApiV1FavoritesListsListIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/lists/${queryArg.listId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Favorites'],
      }),
      listFavoriteItemsApiV1FavoritesListsListIdItemsGet: build.query<
        ListFavoriteItemsApiV1FavoritesListsListIdItemsGetApiResponse,
        ListFavoriteItemsApiV1FavoritesListsListIdItemsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/lists/${queryArg.listId}/items`,
          params: {
            targetType: queryArg.targetType,
            cursor: queryArg.cursor,
            limit: queryArg.limit,
          },
        }),
        providesTags: ['Favorites'],
      }),
      addFavoriteItemApiV1FavoritesItemsPost: build.mutation<
        AddFavoriteItemApiV1FavoritesItemsPostApiResponse,
        AddFavoriteItemApiV1FavoritesItemsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/items`,
          method: 'POST',
          body: queryArg.addFavoriteItemRequest,
        }),
        invalidatesTags: ['Favorites'],
      }),
      removeFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDelete: build.mutation<
        RemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteApiResponse,
        RemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/lists/${queryArg.listId}/items/${queryArg.targetType}/${queryArg.targetId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Favorites'],
      }),
      moveFavoriteItemApiV1FavoritesItemsMovePost: build.mutation<
        MoveFavoriteItemApiV1FavoritesItemsMovePostApiResponse,
        MoveFavoriteItemApiV1FavoritesItemsMovePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/items/move`,
          method: 'POST',
          body: queryArg.moveFavoriteItemRequest,
        }),
        invalidatesTags: ['Favorites'],
      }),
      checkFavoritedApiV1FavoritesCheckPost: build.mutation<
        CheckFavoritedApiV1FavoritesCheckPostApiResponse,
        CheckFavoritedApiV1FavoritesCheckPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/favorites/check`,
          method: 'POST',
          body: queryArg.checkFavoritedRequest,
        }),
        invalidatesTags: ['Favorites'],
      }),
      requestUploadApiV1AdminMediaUploadPost: build.mutation<
        RequestUploadApiV1AdminMediaUploadPostApiResponse,
        RequestUploadApiV1AdminMediaUploadPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/upload`,
          method: 'POST',
          body: queryArg.uploadRequest,
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      reuploadApiV1AdminMediaStorageObjectIdReuploadPost: build.mutation<
        ReuploadApiV1AdminMediaStorageObjectIdReuploadPostApiResponse,
        ReuploadApiV1AdminMediaStorageObjectIdReuploadPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}/reupload`,
          method: 'POST',
          body: queryArg.reuploadRequest,
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      confirmUploadApiV1AdminMediaStorageObjectIdConfirmPost: build.mutation<
        ConfirmUploadApiV1AdminMediaStorageObjectIdConfirmPostApiResponse,
        ConfirmUploadApiV1AdminMediaStorageObjectIdConfirmPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}/confirm`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      streamStatusApiV1AdminMediaStorageObjectIdStatusGet: build.query<
        StreamStatusApiV1AdminMediaStorageObjectIdStatusGetApiResponse,
        StreamStatusApiV1AdminMediaStorageObjectIdStatusGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}/status`,
        }),
        providesTags: ['Admin / Media'],
      }),
      getMetadataApiV1AdminMediaStorageObjectIdGet: build.query<
        GetMetadataApiV1AdminMediaStorageObjectIdGetApiResponse,
        GetMetadataApiV1AdminMediaStorageObjectIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}`,
        }),
        providesTags: ['Admin / Media'],
      }),
      deleteMediaApiV1AdminMediaStorageObjectIdDelete: build.mutation<
        DeleteMediaApiV1AdminMediaStorageObjectIdDeleteApiResponse,
        DeleteMediaApiV1AdminMediaStorageObjectIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      importExternalApiV1AdminMediaExternalPost: build.mutation<
        ImportExternalApiV1AdminMediaExternalPostApiResponse,
        ImportExternalApiV1AdminMediaExternalPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/external`,
          method: 'POST',
          body: queryArg.externalImportRequest,
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      requestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPost: build.mutation<
        RequestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPostApiResponse,
        RequestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/media/${queryArg.storageObjectId}/remove-background`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Media'],
      }),
      listPickupPointsApiV1StorefrontLogisticsPickupPointsPost: build.mutation<
        ListPickupPointsApiV1StorefrontLogisticsPickupPointsPostApiResponse,
        ListPickupPointsApiV1StorefrontLogisticsPickupPointsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/storefront/logistics/pickup-points`,
          method: 'POST',
          body: queryArg.pickupPointsRequest,
        }),
        invalidatesTags: ['Storefront / Logistics'],
      }),
      listProviderAccountsApiV1AdminLogisticsProviderAccountsGet: build.query<
        ListProviderAccountsApiV1AdminLogisticsProviderAccountsGetApiResponse,
        ListProviderAccountsApiV1AdminLogisticsProviderAccountsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/provider-accounts`,
          params: {
            providerCode: queryArg.providerCode,
            onlyActive: queryArg.onlyActive,
          },
        }),
        providesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      createProviderAccountApiV1AdminLogisticsProviderAccountsPost: build.mutation<
        CreateProviderAccountApiV1AdminLogisticsProviderAccountsPostApiResponse,
        CreateProviderAccountApiV1AdminLogisticsProviderAccountsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/provider-accounts`,
          method: 'POST',
          body: queryArg.createProviderAccountRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      getProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGet: build.query<
        GetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetApiResponse,
        GetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/provider-accounts/${queryArg.accountId}`,
        }),
        providesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      updateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPut: build.mutation<
        UpdateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPutApiResponse,
        UpdateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPutApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/provider-accounts/${queryArg.accountId}`,
          method: 'PUT',
          body: queryArg.updateProviderAccountRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      deleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDelete: build.mutation<
        DeleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDeleteApiResponse,
        DeleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/provider-accounts/${queryArg.accountId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      setProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePost:
        build.mutation<
          SetProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePostApiResponse,
          SetProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePostApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/logistics/provider-accounts/${queryArg.accountId}/active`,
            method: 'POST',
            body: queryArg.setProviderAccountActiveRequest,
          }),
          invalidatesTags: ['Admin / Logistics / Provider Accounts'],
        }),
      refreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPost: build.mutation<
        RefreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPostApiResponse,
        RefreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPostApiArg
      >({
        query: () => ({
          url: `/api/v1/admin/logistics/provider-accounts/refresh`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Logistics / Provider Accounts'],
      }),
      calculateRatesApiV1AdminLogisticsRatesPost: build.mutation<
        CalculateRatesApiV1AdminLogisticsRatesPostApiResponse,
        CalculateRatesApiV1AdminLogisticsRatesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/rates`,
          method: 'POST',
          body: queryArg.calculateRatesRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      quoteForPickupPointApiV1AdminLogisticsRatesQuotePost: build.mutation<
        QuoteForPickupPointApiV1AdminLogisticsRatesQuotePostApiResponse,
        QuoteForPickupPointApiV1AdminLogisticsRatesQuotePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/rates/quote`,
          method: 'POST',
          body: queryArg.rateQuoteRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      listAdminShipmentsApiV1AdminLogisticsShipmentsGet: build.query<
        ListAdminShipmentsApiV1AdminLogisticsShipmentsGetApiResponse,
        ListAdminShipmentsApiV1AdminLogisticsShipmentsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments`,
          params: {
            provider: queryArg.provider,
            status: queryArg.status,
            orderId: queryArg.orderId,
            createdAfter: queryArg.createdAfter,
            createdBefore: queryArg.createdBefore,
            trackingNumberContains: queryArg.trackingNumberContains,
            limit: queryArg.limit,
            cursor: queryArg.cursor,
          },
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      createShipmentApiV1AdminLogisticsShipmentsPost: build.mutation<
        CreateShipmentApiV1AdminLogisticsShipmentsPostApiResponse,
        CreateShipmentApiV1AdminLogisticsShipmentsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments`,
          method: 'POST',
          body: queryArg.createShipmentRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      bookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPost: build.mutation<
        BookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPostApiResponse,
        BookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/book`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      cancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPost: build.mutation<
        CancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPostApiResponse,
        CancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/cancel`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      getShipmentApiV1AdminLogisticsShipmentsShipmentIdGet: build.query<
        GetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetApiResponse,
        GetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      getTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGet: build.query<
        GetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetApiResponse,
        GetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/tracking`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      listPickupPointsApiV1AdminLogisticsPickupPointsPost: build.mutation<
        ListPickupPointsApiV1AdminLogisticsPickupPointsPostApiResponse,
        ListPickupPointsApiV1AdminLogisticsPickupPointsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/pickup-points`,
          method: 'POST',
          body: queryArg.pickupPointsRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      listAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPost: build.mutation<
        ListAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPostApiResponse,
        ListAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/intakes/available-days`,
          method: 'POST',
          body: queryArg.availableIntakeDaysRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      createIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePost: build.mutation<
        CreateIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePostApiResponse,
        CreateIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/intake`,
          method: 'POST',
          body: queryArg.createIntakeRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      getIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGet: build.query<
        GetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetApiResponse,
        GetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/intakes/${queryArg.providerCode}/${queryArg.providerIntakeId}`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      cancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDelete: build.mutation<
        CancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDeleteApiResponse,
        CancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/intakes/${queryArg.providerCode}/${queryArg.providerIntakeId}`,
          method: 'DELETE',
          params: {
            shipmentId: queryArg.shipmentId,
          },
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      getDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGet: build.query<
        GetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetApiResponse,
        GetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/delivery-intervals`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      estimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePost: build.mutation<
        EstimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePostApiResponse,
        EstimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/delivery-intervals/estimate`,
          method: 'POST',
          body: queryArg.estimatedDeliveryIntervalsRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      registerClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPost: build.mutation<
        RegisterClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPostApiResponse,
        RegisterClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/return`,
          method: 'POST',
          body: queryArg.clientReturnRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      registerRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPost: build.mutation<
        RegisterRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPostApiResponse,
        RegisterRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/refusal`,
          method: 'POST',
          body: queryArg.refusalRequestSchema,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      checkReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPost: build.mutation<
        CheckReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPostApiResponse,
        CheckReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/reverse-availability`,
          method: 'POST',
          body: queryArg.reverseAvailabilityRequestSchema,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      getActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGet: build.query<
        GetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetApiResponse,
        GetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/actual-delivery-info`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      editOrderApiV1AdminLogisticsShipmentsShipmentIdEditPost: build.mutation<
        EditOrderApiV1AdminLogisticsShipmentsShipmentIdEditPostApiResponse,
        EditOrderApiV1AdminLogisticsShipmentsShipmentIdEditPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/edit`,
          method: 'POST',
          body: queryArg.editOrderRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      editOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPost: build.mutation<
        EditOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPostApiResponse,
        EditOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/edit-packages`,
          method: 'POST',
          body: queryArg.editPackagesRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      editOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPost: build.mutation<
        EditOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPostApiResponse,
        EditOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/edit-items`,
          method: 'POST',
          body: queryArg.editOrderItemsRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      removeOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPost: build.mutation<
        RemoveOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPostApiResponse,
        RemoveOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/shipments/${queryArg.shipmentId}/remove-items`,
          method: 'POST',
          body: queryArg.removeOrderItemsRequest,
        }),
        invalidatesTags: ['Admin / Logistics / Shipments'],
      }),
      getEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGet: build.query<
        GetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetApiResponse,
        GetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/edit-tasks/${queryArg.providerCode}/${queryArg.taskId}`,
        }),
        providesTags: ['Admin / Logistics / Shipments'],
      }),
      editCdekOrderApiV1AdminLogisticsCdekOrdersEditPost: build.mutation<
        EditCdekOrderApiV1AdminLogisticsCdekOrdersEditPostApiResponse,
        EditCdekOrderApiV1AdminLogisticsCdekOrdersEditPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/orders/edit`,
          method: 'POST',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      lookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGet: build.query<
        LookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetApiResponse,
        LookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/orders/lookup`,
          params: {
            cdekNumber: queryArg.cdekNumber,
            imNumber: queryArg.imNumber,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGet: build.query<
        ListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetApiResponse,
        ListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/orders/${queryArg.orderUuid}/intakes`,
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      downloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGet: build.query<
        DownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetApiResponse,
        DownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/shipments/${queryArg.shipmentId}/barcode`,
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      registerCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPost: build.mutation<
        RegisterCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPostApiResponse,
        RegisterCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/delivery-agreements`,
          method: 'POST',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      getCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGet:
        build.query<
          GetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetApiResponse,
          GetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetApiArg
        >({
          query: (queryArg) => ({
            url: `/api/v1/admin/logistics/cdek/delivery-agreements/${queryArg.agreementUuid}`,
          }),
          providesTags: ['Admin / Logistics / CDEK'],
        }),
      createCdekPrealertApiV1AdminLogisticsCdekPrealertsPost: build.mutation<
        CreateCdekPrealertApiV1AdminLogisticsCdekPrealertsPostApiResponse,
        CreateCdekPrealertApiV1AdminLogisticsCdekPrealertsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/prealerts`,
          method: 'POST',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      getCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGet: build.query<
        GetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetApiResponse,
        GetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/prealerts/${queryArg.prealertUuid}`,
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      getCdekChecksApiV1AdminLogisticsCdekChecksGet: build.query<
        GetCdekChecksApiV1AdminLogisticsCdekChecksGetApiResponse,
        GetCdekChecksApiV1AdminLogisticsCdekChecksGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/checks`,
          params: {
            orderUuid: queryArg.orderUuid,
            cdekNumber: queryArg.cdekNumber,
            date: queryArg.date,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      getCdekRegistriesApiV1AdminLogisticsCdekRegistriesGet: build.query<
        GetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetApiResponse,
        GetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/registries`,
          params: {
            date: queryArg.date,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      checkCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPost: build.mutation<
        CheckCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPostApiResponse,
        CheckCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/restrictions`,
          method: 'POST',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      getCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPost: build.mutation<
        GetCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPostApiResponse,
        GetCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/photos`,
          method: 'POST',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      changeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatch: build.mutation<
        ChangeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatchApiResponse,
        ChangeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/intakes/status`,
          method: 'PATCH',
          body: queryArg.cdekRawPayloadRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekTariffsApiV1AdminLogisticsCdekTariffsGet: build.query<
        ListCdekTariffsApiV1AdminLogisticsCdekTariffsGetApiResponse,
        ListCdekTariffsApiV1AdminLogisticsCdekTariffsGetApiArg
      >({
        query: () => ({ url: `/api/v1/admin/logistics/cdek/tariffs` }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      suggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGet: build.query<
        SuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetApiResponse,
        SuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/locations/suggest`,
          params: {
            name: queryArg.name,
            countryCode: queryArg.countryCode,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGet: build.query<
        ListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetApiResponse,
        ListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/locations/cities`,
          params: {
            city: queryArg.city,
            countryCodes: queryArg.countryCodes,
            postalCode: queryArg.postalCode,
            code: queryArg.code,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGet: build.query<
        ListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetApiResponse,
        ListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/locations/regions`,
          params: {
            countryCodes: queryArg.countryCodes,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGet: build.query<
        ListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetApiResponse,
        ListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/locations/postal-codes`,
          params: {
            cityCode: queryArg.cityCode,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      resolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGet: build.query<
        ResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetApiResponse,
        ResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/locations/by-coordinates`,
          params: {
            latitude: queryArg.latitude,
            longitude: queryArg.longitude,
          },
        }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      listCdekWebhooksApiV1AdminLogisticsCdekWebhooksGet: build.query<
        ListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetApiResponse,
        ListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetApiArg
      >({
        query: () => ({ url: `/api/v1/admin/logistics/cdek/webhooks` }),
        providesTags: ['Admin / Logistics / CDEK'],
      }),
      createCdekWebhookApiV1AdminLogisticsCdekWebhooksPost: build.mutation<
        CreateCdekWebhookApiV1AdminLogisticsCdekWebhooksPostApiResponse,
        CreateCdekWebhookApiV1AdminLogisticsCdekWebhooksPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/webhooks`,
          method: 'POST',
          body: queryArg.cdekWebhookSubscriptionRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      syncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPost: build.mutation<
        SyncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPostApiResponse,
        SyncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/webhooks/sync`,
          method: 'POST',
          body: queryArg.cdekWebhookSyncRequest,
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      deleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDelete: build.mutation<
        DeleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDeleteApiResponse,
        DeleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/logistics/cdek/webhooks/${queryArg.subscriptionUuid}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Admin / Logistics / CDEK'],
      }),
      receiveWebhookApiV1WebhooksLogisticsProviderCodePost: build.mutation<
        ReceiveWebhookApiV1WebhooksLogisticsProviderCodePostApiResponse,
        ReceiveWebhookApiV1WebhooksLogisticsProviderCodePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/webhooks/logistics/${queryArg.providerCode}`,
          method: 'POST',
        }),
        invalidatesTags: ['Webhooks / Logistics'],
      }),
      getPaymentIntentApiV1PaymentsIntentsIntentIdGet: build.query<
        GetPaymentIntentApiV1PaymentsIntentsIntentIdGetApiResponse,
        GetPaymentIntentApiV1PaymentsIntentsIntentIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/payments/intents/${queryArg.intentId}`,
        }),
        providesTags: ['Payments'],
      }),
      simulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePost: build.mutation<
        SimulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePostApiResponse,
        SimulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/payments/intents/${queryArg.intentId}/_simulate-capture`,
          method: 'POST',
          body: queryArg.simulateCaptureRequest,
        }),
        invalidatesTags: ['Payments'],
      }),
      providerWebhookApiV1WebhooksPaymentsProviderPost: build.mutation<
        ProviderWebhookApiV1WebhooksPaymentsProviderPostApiResponse,
        ProviderWebhookApiV1WebhooksPaymentsProviderPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/webhooks/payments/${queryArg.provider}`,
          method: 'POST',
          body: queryArg.payload,
        }),
        invalidatesTags: ['Webhooks / Payments'],
      }),
      createRecipientApiV1RecipientsPost: build.mutation<
        CreateRecipientApiV1RecipientsPostApiResponse,
        CreateRecipientApiV1RecipientsPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/recipients`,
          method: 'POST',
          body: queryArg.createRecipientRequest,
        }),
        invalidatesTags: ['Recipients'],
      }),
      listMyRecipientsApiV1RecipientsGet: build.query<
        ListMyRecipientsApiV1RecipientsGetApiResponse,
        ListMyRecipientsApiV1RecipientsGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/recipients`,
          params: {
            includeArchived: queryArg.includeArchived,
          },
        }),
        providesTags: ['Recipients'],
      }),
      getRecipientApiV1RecipientsRecipientIdGet: build.query<
        GetRecipientApiV1RecipientsRecipientIdGetApiResponse,
        GetRecipientApiV1RecipientsRecipientIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/recipients/${queryArg.recipientId}`,
        }),
        providesTags: ['Recipients'],
      }),
      updateRecipientApiV1RecipientsRecipientIdPatch: build.mutation<
        UpdateRecipientApiV1RecipientsRecipientIdPatchApiResponse,
        UpdateRecipientApiV1RecipientsRecipientIdPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/recipients/${queryArg.recipientId}`,
          method: 'PATCH',
          body: queryArg.updateRecipientRequest,
          headers: {
            'If-Match': queryArg['If-Match'],
          },
        }),
        invalidatesTags: ['Recipients'],
      }),
      archiveRecipientApiV1RecipientsRecipientIdDelete: build.mutation<
        ArchiveRecipientApiV1RecipientsRecipientIdDeleteApiResponse,
        ArchiveRecipientApiV1RecipientsRecipientIdDeleteApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/recipients/${queryArg.recipientId}`,
          method: 'DELETE',
        }),
        invalidatesTags: ['Recipients'],
      }),
      createOrderApiV1OrdersPost: build.mutation<
        CreateOrderApiV1OrdersPostApiResponse,
        CreateOrderApiV1OrdersPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders`,
          method: 'POST',
          body: queryArg.createOrderRequest,
        }),
        invalidatesTags: ['Orders'],
      }),
      listMyOrdersApiV1OrdersGet: build.query<
        ListMyOrdersApiV1OrdersGetApiResponse,
        ListMyOrdersApiV1OrdersGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders`,
          params: {
            limit: queryArg.limit,
            cursor: queryArg.cursor,
          },
        }),
        providesTags: ['Orders'],
      }),
      getOrderApiV1OrdersOrderIdGet: build.query<
        GetOrderApiV1OrdersOrderIdGetApiResponse,
        GetOrderApiV1OrdersOrderIdGetApiArg
      >({
        query: (queryArg) => ({ url: `/api/v1/orders/${queryArg.orderId}` }),
        providesTags: ['Orders'],
      }),
      getOrderTrackingApiV1OrdersOrderIdTrackingGet: build.query<
        GetOrderTrackingApiV1OrdersOrderIdTrackingGetApiResponse,
        GetOrderTrackingApiV1OrdersOrderIdTrackingGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders/${queryArg.orderId}/tracking`,
        }),
        providesTags: ['Orders'],
      }),
      cancelOrderApiV1OrdersOrderIdCancelPost: build.mutation<
        CancelOrderApiV1OrdersOrderIdCancelPostApiResponse,
        CancelOrderApiV1OrdersOrderIdCancelPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders/${queryArg.orderId}/cancel`,
          method: 'POST',
          body: queryArg.cancelOrderRequest,
        }),
        invalidatesTags: ['Orders'],
      }),
      refreshRecipientApiV1OrdersOrderIdRefreshRecipientPost: build.mutation<
        RefreshRecipientApiV1OrdersOrderIdRefreshRecipientPostApiResponse,
        RefreshRecipientApiV1OrdersOrderIdRefreshRecipientPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders/${queryArg.orderId}/refresh-recipient`,
          method: 'POST',
        }),
        invalidatesTags: ['Orders'],
      }),
      changePickupPointApiV1OrdersOrderIdPickupPointPatch: build.mutation<
        ChangePickupPointApiV1OrdersOrderIdPickupPointPatchApiResponse,
        ChangePickupPointApiV1OrdersOrderIdPickupPointPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/orders/${queryArg.orderId}/pickup-point`,
          method: 'PATCH',
          body: queryArg.changePickupPointRequest,
        }),
        invalidatesTags: ['Orders'],
      }),
      adminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGet: build.query<
        AdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetApiResponse,
        AdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetApiArg
      >({
        query: () => ({
          url: `/api/v1/admin/orders/_meta/cancellation-reasons`,
        }),
        providesTags: ['Admin / Orders'],
      }),
      adminListOrdersApiV1AdminOrdersGet: build.query<
        AdminListOrdersApiV1AdminOrdersGetApiResponse,
        AdminListOrdersApiV1AdminOrdersGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders`,
          params: {
            statuses: queryArg.statuses,
            limit: queryArg.limit,
            cursor: queryArg.cursor,
          },
        }),
        providesTags: ['Admin / Orders'],
      }),
      adminGetOrderApiV1AdminOrdersOrderIdGet: build.query<
        AdminGetOrderApiV1AdminOrdersOrderIdGetApiResponse,
        AdminGetOrderApiV1AdminOrdersOrderIdGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}`,
        }),
        providesTags: ['Admin / Orders'],
      }),
      adminGetHistoryApiV1AdminOrdersOrderIdHistoryGet: build.query<
        AdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetApiResponse,
        AdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/history`,
        }),
        providesTags: ['Admin / Orders'],
      }),
      adminProcureOrderApiV1AdminOrdersOrderIdProcurePost: build.mutation<
        AdminProcureOrderApiV1AdminOrdersOrderIdProcurePostApiResponse,
        AdminProcureOrderApiV1AdminOrdersOrderIdProcurePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/procure`,
          method: 'POST',
          body: queryArg.procureOrderRequest,
        }),
        invalidatesTags: ['Admin / Orders'],
      }),
      adminHoldOrderApiV1AdminOrdersOrderIdHoldPost: build.mutation<
        AdminHoldOrderApiV1AdminOrdersOrderIdHoldPostApiResponse,
        AdminHoldOrderApiV1AdminOrdersOrderIdHoldPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/hold`,
          method: 'POST',
          body: queryArg.holdOrderRequest,
        }),
        invalidatesTags: ['Admin / Orders'],
      }),
      adminResumeOrderApiV1AdminOrdersOrderIdResumePost: build.mutation<
        AdminResumeOrderApiV1AdminOrdersOrderIdResumePostApiResponse,
        AdminResumeOrderApiV1AdminOrdersOrderIdResumePostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/resume`,
          method: 'POST',
        }),
        invalidatesTags: ['Admin / Orders'],
      }),
      adminForceCancelApiV1AdminOrdersOrderIdForceCancelPost: build.mutation<
        AdminForceCancelApiV1AdminOrdersOrderIdForceCancelPostApiResponse,
        AdminForceCancelApiV1AdminOrdersOrderIdForceCancelPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/force-cancel`,
          method: 'POST',
          body: queryArg.cancelOrderRequest,
        }),
        invalidatesTags: ['Admin / Orders'],
      }),
      adminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatch: build.mutation<
        AdminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatchApiResponse,
        AdminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatchApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/admin/orders/${queryArg.orderId}/pickup-point`,
          method: 'PATCH',
          body: queryArg.changePickupPointRequest,
        }),
        invalidatesTags: ['Admin / Orders'],
      }),
      dobropostWebhookApiV1WebhooksDobropostTokenPost: build.mutation<
        DobropostWebhookApiV1WebhooksDobropostTokenPostApiResponse,
        DobropostWebhookApiV1WebhooksDobropostTokenPostApiArg
      >({
        query: (queryArg) => ({
          url: `/api/v1/webhooks/dobropost/${queryArg.token}`,
          method: 'POST',
          body: queryArg.payload,
        }),
        invalidatesTags: ['Webhooks / DobroPost'],
      }),
      healthCheckHealthGet: build.query<
        HealthCheckHealthGetApiResponse,
        HealthCheckHealthGetApiArg
      >({
        query: () => ({ url: `/health` }),
        providesTags: ['System'],
      }),
    }),
    overrideExisting: false,
  });
export { injectedRtkApi as generatedApi };
export type ListCountriesApiV1GeoCountriesGetApiResponse =
  /** status 200 Successful Response */ CountryListReadModel;
export type ListCountriesApiV1GeoCountriesGetApiArg = {
  /** Filter translations to this language code */
  lang?: string | null;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type ListCurrenciesApiV1GeoCurrenciesGetApiResponse =
  /** status 200 Successful Response */ CurrencyListReadModel;
export type ListCurrenciesApiV1GeoCurrenciesGetApiArg = {
  /** Filter translations to this language code */
  lang?: string | null;
  /** Include inactive currencies */
  includeInactive?: boolean;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type ListLanguagesApiV1GeoLanguagesGetApiResponse =
  /** status 200 Successful Response */ LanguageListReadModel;
export type ListLanguagesApiV1GeoLanguagesGetApiArg = {
  /** Include inactive languages */
  includeInactive?: boolean;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type GetCountryApiV1GeoCountriesAlpha2GetApiResponse =
  /** status 200 Successful Response */ CountryReadModel;
export type GetCountryApiV1GeoCountriesAlpha2GetApiArg = {
  alpha2: string;
  /** Filter translations to this language code */
  lang?: string | null;
};
export type GetCurrencyApiV1GeoCurrenciesCodeGetApiResponse =
  /** status 200 Successful Response */ CurrencyReadModel;
export type GetCurrencyApiV1GeoCurrenciesCodeGetApiArg = {
  code: string;
  /** Filter translations to this language code */
  lang?: string | null;
};
export type GetLanguageApiV1GeoLanguagesCodeGetApiResponse =
  /** status 200 Successful Response */ LanguageReadModel;
export type GetLanguageApiV1GeoLanguagesCodeGetApiArg = {
  code: string;
};
export type GetSubdivisionApiV1GeoSubdivisionsCodeGetApiResponse =
  /** status 200 Successful Response */ SubdivisionReadModel;
export type GetSubdivisionApiV1GeoSubdivisionsCodeGetApiArg = {
  code: string;
  /** Filter translations to this language code */
  lang?: string | null;
};
export type ListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetApiResponse =
  /** status 200 Successful Response */ CurrencyListReadModel;
export type ListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetApiArg = {
  countryCode: string;
  /** Filter translations to this language code */
  lang?: string | null;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type ListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetApiResponse =
  /** status 200 Successful Response */ SubdivisionListReadModel;
export type ListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetApiArg = {
  countryCode: string;
  /** Filter translations to this language code */
  lang?: string | null;
  /** Search subdivisions by translated name (requires lang) */
  search?: string | null;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type GetDistrictApiV1GeoDistrictsDistrictIdGetApiResponse =
  /** status 200 Successful Response */ DistrictReadModel;
export type GetDistrictApiV1GeoDistrictsDistrictIdGetApiArg = {
  districtId: string;
  /** Filter translations to this language code */
  lang?: string | null;
};
export type ListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetApiResponse =
  /** status 200 Successful Response */ DistrictListReadModel;
export type ListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetApiArg = {
  subdivisionCode: string;
  /** Filter translations to this language code */
  lang?: string | null;
  /** Search districts by translated name */
  search?: string | null;
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
};
export type CreateCountryApiV1AdminGeoCountriesPostApiResponse =
  /** status 201 Successful Response */ CountryReadModel;
export type CreateCountryApiV1AdminGeoCountriesPostApiArg = {
  createCountryRequest: CreateCountryRequest;
};
export type UpdateCountryApiV1AdminGeoCountriesAlpha2PatchApiResponse =
  /** status 200 Successful Response */ CountryReadModel;
export type UpdateCountryApiV1AdminGeoCountriesAlpha2PatchApiArg = {
  alpha2: string;
  updateCountryRequest: UpdateCountryRequest;
};
export type DeleteCountryApiV1AdminGeoCountriesAlpha2DeleteApiResponse = unknown;
export type DeleteCountryApiV1AdminGeoCountriesAlpha2DeleteApiArg = {
  alpha2: string;
};
export type UpsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPutApiResponse =
  /** status 200 Successful Response */ CountryTranslationReadModel[];
export type UpsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPutApiArg = {
  alpha2: string;
  upsertCountryTranslationsRequest: UpsertCountryTranslationsRequest;
};
export type SetCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPutApiResponse =
  /** status 200 Successful Response */ CountryCurrencyLinkReadModel[];
export type SetCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPutApiArg = {
  alpha2: string;
  setCountryCurrenciesRequest: SetCountryCurrenciesRequest;
};
export type CreateCurrencyApiV1AdminGeoCurrenciesPostApiResponse =
  /** status 201 Successful Response */ CurrencyReadModel;
export type CreateCurrencyApiV1AdminGeoCurrenciesPostApiArg = {
  createCurrencyRequest: CreateCurrencyRequest;
};
export type UpdateCurrencyApiV1AdminGeoCurrenciesCodePatchApiResponse =
  /** status 200 Successful Response */ CurrencyReadModel;
export type UpdateCurrencyApiV1AdminGeoCurrenciesCodePatchApiArg = {
  code: string;
  updateCurrencyRequest: UpdateCurrencyRequest;
};
export type DeleteCurrencyApiV1AdminGeoCurrenciesCodeDeleteApiResponse = unknown;
export type DeleteCurrencyApiV1AdminGeoCurrenciesCodeDeleteApiArg = {
  code: string;
};
export type UpsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPutApiResponse =
  /** status 200 Successful Response */ CurrencyTranslationReadModel[];
export type UpsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPutApiArg = {
  code: string;
  upsertCurrencyTranslationsRequest: UpsertCurrencyTranslationsRequest;
};
export type CreateLanguageApiV1AdminGeoLanguagesPostApiResponse =
  /** status 201 Successful Response */ LanguageReadModel;
export type CreateLanguageApiV1AdminGeoLanguagesPostApiArg = {
  createLanguageRequest: CreateLanguageRequest;
};
export type UpdateLanguageApiV1AdminGeoLanguagesCodePatchApiResponse =
  /** status 200 Successful Response */ LanguageReadModel;
export type UpdateLanguageApiV1AdminGeoLanguagesCodePatchApiArg = {
  code: string;
  updateLanguageRequest: UpdateLanguageRequest;
};
export type DeleteLanguageApiV1AdminGeoLanguagesCodeDeleteApiResponse = unknown;
export type DeleteLanguageApiV1AdminGeoLanguagesCodeDeleteApiArg = {
  code: string;
};
export type CreateSubdivisionApiV1AdminGeoSubdivisionsPostApiResponse =
  /** status 201 Successful Response */ SubdivisionReadModel;
export type CreateSubdivisionApiV1AdminGeoSubdivisionsPostApiArg = {
  createSubdivisionRequest: CreateSubdivisionRequest;
};
export type UpdateSubdivisionApiV1AdminGeoSubdivisionsCodePatchApiResponse =
  /** status 200 Successful Response */ SubdivisionReadModel;
export type UpdateSubdivisionApiV1AdminGeoSubdivisionsCodePatchApiArg = {
  code: string;
  updateSubdivisionRequest: UpdateSubdivisionRequest;
};
export type DeleteSubdivisionApiV1AdminGeoSubdivisionsCodeDeleteApiResponse = unknown;
export type DeleteSubdivisionApiV1AdminGeoSubdivisionsCodeDeleteApiArg = {
  code: string;
};
export type UpsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPutApiResponse =
  /** status 200 Successful Response */ SubdivisionTranslationReadModel[];
export type UpsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPutApiArg = {
  code: string;
  upsertSubdivisionTranslationsRequest: UpsertSubdivisionTranslationsRequest;
};
export type ListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetApiResponse =
  /** status 200 Successful Response */ SubdivisionTypeListReadModel;
export type ListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetApiArg = {
  offset?: number;
  limit?: number;
};
export type CreateSubdivisionTypeApiV1AdminGeoSubdivisionTypesPostApiResponse =
  /** status 201 Successful Response */ SubdivisionTypeReadModel;
export type CreateSubdivisionTypeApiV1AdminGeoSubdivisionTypesPostApiArg = {
  createSubdivisionTypeRequest: CreateSubdivisionTypeRequest;
};
export type UpdateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatchApiResponse =
  /** status 200 Successful Response */ SubdivisionTypeReadModel;
export type UpdateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatchApiArg = {
  code: string;
  updateSubdivisionTypeRequest: UpdateSubdivisionTypeRequest;
};
export type DeleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDeleteApiResponse = unknown;
export type DeleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDeleteApiArg = {
  code: string;
};
export type UpsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPutApiResponse =
  /** status 200 Successful Response */ SubdivisionTypeTranslationReadModel[];
export type UpsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPutApiArg =
  {
    code: string;
    upsertSubdivisionTypeTranslationsRequest: UpsertSubdivisionTypeTranslationsRequest;
  };
export type CreateDistrictApiV1AdminGeoDistrictsPostApiResponse =
  /** status 201 Successful Response */ DistrictReadModel;
export type CreateDistrictApiV1AdminGeoDistrictsPostApiArg = {
  createDistrictRequest: CreateDistrictRequest;
};
export type UpdateDistrictApiV1AdminGeoDistrictsDistrictIdPatchApiResponse =
  /** status 200 Successful Response */ DistrictReadModel;
export type UpdateDistrictApiV1AdminGeoDistrictsDistrictIdPatchApiArg = {
  districtId: string;
  updateDistrictRequest: UpdateDistrictRequest;
};
export type DeleteDistrictApiV1AdminGeoDistrictsDistrictIdDeleteApiResponse = unknown;
export type DeleteDistrictApiV1AdminGeoDistrictsDistrictIdDeleteApiArg = {
  districtId: string;
};
export type UpsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPutApiResponse =
  /** status 200 Successful Response */ DistrictTranslationReadModel[];
export type UpsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPutApiArg = {
  districtId: string;
  upsertDistrictTranslationsRequest: UpsertDistrictTranslationsRequest;
};
export type ListDistrictTypesApiV1AdminGeoDistrictTypesGetApiResponse =
  /** status 200 Successful Response */ DistrictTypeListReadModel;
export type ListDistrictTypesApiV1AdminGeoDistrictTypesGetApiArg = {
  offset?: number;
  limit?: number;
};
export type CreateDistrictTypeApiV1AdminGeoDistrictTypesPostApiResponse =
  /** status 201 Successful Response */ DistrictTypeReadModel;
export type CreateDistrictTypeApiV1AdminGeoDistrictTypesPostApiArg = {
  createDistrictTypeRequest: CreateDistrictTypeRequest;
};
export type UpdateDistrictTypeApiV1AdminGeoDistrictTypesCodePatchApiResponse =
  /** status 200 Successful Response */ DistrictTypeReadModel;
export type UpdateDistrictTypeApiV1AdminGeoDistrictTypesCodePatchApiArg = {
  code: string;
  updateDistrictTypeRequest: UpdateDistrictTypeRequest;
};
export type DeleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDeleteApiResponse = unknown;
export type DeleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDeleteApiArg = {
  code: string;
};
export type UpsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPutApiResponse =
  /** status 200 Successful Response */ DistrictTypeTranslationReadModel[];
export type UpsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPutApiArg = {
  code: string;
  upsertDistrictTypeTranslationsRequest: UpsertDistrictTypeTranslationsRequest;
};
export type RegisterApiV1AuthRegisterPostApiResponse =
  /** status 201 Successful Response */ RegisterResponse;
export type RegisterApiV1AuthRegisterPostApiArg = {
  registerRequest: RegisterRequest;
};
export type LoginApiV1AuthLoginPostApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type LoginApiV1AuthLoginPostApiArg = {
  loginRequest: LoginRequest;
};
export type LoginTelegramApiV1AuthTelegramPostApiResponse =
  /** status 200 Successful Response */ TelegramTokenResponse;
export type LoginTelegramApiV1AuthTelegramPostApiArg = void;
export type RefreshTokenApiV1AuthRefreshPostApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type RefreshTokenApiV1AuthRefreshPostApiArg = {
  refreshTokenRequest: RefreshTokenRequest;
};
export type LogoutApiV1AuthLogoutPostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type LogoutApiV1AuthLogoutPostApiArg = void;
export type LogoutAllApiV1AuthLogoutAllPostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type LogoutAllApiV1AuthLogoutAllPostApiArg = void;
export type ValidateInvitationApiV1InvitationsTokenValidateGetApiResponse =
  /** status 200 Successful Response */ InvitationInfoResponse;
export type ValidateInvitationApiV1InvitationsTokenValidateGetApiArg = {
  token: string;
};
export type AcceptInvitationApiV1InvitationsTokenAcceptPostApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type AcceptInvitationApiV1InvitationsTokenAcceptPostApiArg = {
  token: string;
  acceptInvitationRequest: AcceptInvitationRequest;
};
export type GetMyProfileApiV1ProfileMeGetApiResponse =
  /** status 200 Successful Response */ ProfileResponse;
export type GetMyProfileApiV1ProfileMeGetApiArg = void;
export type DeleteMyAccountApiV1ProfileMeDeleteApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type DeleteMyAccountApiV1ProfileMeDeleteApiArg = void;
export type UpdateProfileApiV1ProfileMePatchApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type UpdateProfileApiV1ProfileMePatchApiArg = {
  updateProfileRequest: UpdateProfileRequest;
};
export type ChangePasswordApiV1ProfilePasswordPutApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type ChangePasswordApiV1ProfilePasswordPutApiArg = {
  changePasswordRequest: ChangePasswordRequest;
};
export type GetMySessionsApiV1ProfileSessionsGetApiResponse =
  /** status 200 Successful Response */ SessionInfo[];
export type GetMySessionsApiV1ProfileSessionsGetApiArg = void;
export type ListIdentitiesApiV1AdminIdentitiesGetApiResponse =
  /** status 200 Successful Response */ AdminIdentityListResponse;
export type ListIdentitiesApiV1AdminIdentitiesGetApiArg = {
  offset?: number;
  limit?: number;
  search?: string | null;
  roleId?: string | null;
  isActive?: boolean | null;
  sortBy?: string;
  sortOrder?: string;
};
export type GetIdentityDetailApiV1AdminIdentitiesIdentityIdGetApiResponse =
  /** status 200 Successful Response */ AdminIdentityDetailResponse;
export type GetIdentityDetailApiV1AdminIdentitiesIdentityIdGetApiArg = {
  identityId: string;
};
export type AdminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type AdminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePostApiArg = {
  identityId: string;
  adminDeactivateRequest: AdminDeactivateRequest;
};
export type AdminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type AdminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePostApiArg = {
  identityId: string;
};
export type ListRolesApiV1AdminRolesGetApiResponse =
  /** status 200 Successful Response */ RoleWithPermissions[];
export type ListRolesApiV1AdminRolesGetApiArg = void;
export type CreateRoleApiV1AdminRolesPostApiResponse =
  /** status 201 Successful Response */ CreateRoleResponse;
export type CreateRoleApiV1AdminRolesPostApiArg = {
  createRoleRequest: CreateRoleRequest;
};
export type GetRoleDetailApiV1AdminRolesRoleIdGetApiResponse =
  /** status 200 Successful Response */ RoleDetailResponse;
export type GetRoleDetailApiV1AdminRolesRoleIdGetApiArg = {
  roleId: string;
};
export type UpdateRoleApiV1AdminRolesRoleIdPatchApiResponse =
  /** status 200 Successful Response */ RoleDetailResponse;
export type UpdateRoleApiV1AdminRolesRoleIdPatchApiArg = {
  roleId: string;
  updateRoleRequest: UpdateRoleRequest;
};
export type DeleteRoleApiV1AdminRolesRoleIdDeleteApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type DeleteRoleApiV1AdminRolesRoleIdDeleteApiArg = {
  roleId: string;
};
export type SetRolePermissionsApiV1AdminRolesRoleIdPermissionsPutApiResponse =
  /** status 200 Successful Response */ RoleDetailResponse;
export type SetRolePermissionsApiV1AdminRolesRoleIdPermissionsPutApiArg = {
  roleId: string;
  setRolePermissionsRequest: SetRolePermissionsRequest;
};
export type ListPermissionsApiV1AdminPermissionsGetApiResponse =
  /** status 200 Successful Response */ PermissionGroupResponse[];
export type ListPermissionsApiV1AdminPermissionsGetApiArg = void;
export type AssignRoleApiV1AdminIdentitiesIdentityIdRolesPostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type AssignRoleApiV1AdminIdentitiesIdentityIdRolesPostApiArg = {
  identityId: string;
  assignRoleRequest: AssignRoleRequest;
};
export type RevokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDeleteApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type RevokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDeleteApiArg = {
  identityId: string;
  roleId: string;
};
export type ListStaffApiV1AdminStaffGetApiResponse =
  /** status 200 Successful Response */ StaffListResponse;
export type ListStaffApiV1AdminStaffGetApiArg = {
  offset?: number;
  limit?: number;
  search?: string | null;
  roleId?: string | null;
  isActive?: boolean | null;
  sortBy?: string;
  sortOrder?: string;
};
export type InviteStaffApiV1AdminStaffInvitationsPostApiResponse =
  /** status 201 Successful Response */ InviteStaffResponse;
export type InviteStaffApiV1AdminStaffInvitationsPostApiArg = {
  inviteStaffRequest: InviteStaffRequest;
};
export type ListInvitationsApiV1AdminStaffInvitationsGetApiResponse =
  /** status 200 Successful Response */ InvitationListResponse;
export type ListInvitationsApiV1AdminStaffInvitationsGetApiArg = {
  offset?: number;
  limit?: number;
  status?: string | null;
};
export type RevokeInvitationApiV1AdminStaffInvitationsInvitationIdDeleteApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type RevokeInvitationApiV1AdminStaffInvitationsInvitationIdDeleteApiArg = {
  invitationId: string;
};
export type GetStaffDetailApiV1AdminStaffIdentityIdGetApiResponse =
  /** status 200 Successful Response */ StaffDetailResponse;
export type GetStaffDetailApiV1AdminStaffIdentityIdGetApiArg = {
  identityId: string;
};
export type DeactivateStaffApiV1AdminStaffIdentityIdDeactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type DeactivateStaffApiV1AdminStaffIdentityIdDeactivatePostApiArg = {
  identityId: string;
  adminDeactivateRequest: AdminDeactivateRequest;
};
export type ReactivateStaffApiV1AdminStaffIdentityIdReactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type ReactivateStaffApiV1AdminStaffIdentityIdReactivatePostApiArg = {
  identityId: string;
};
export type ListCustomersApiV1AdminCustomersGetApiResponse =
  /** status 200 Successful Response */ CustomerListResponse;
export type ListCustomersApiV1AdminCustomersGetApiArg = {
  offset?: number;
  limit?: number;
  search?: string | null;
  isActive?: boolean | null;
  sortBy?: string;
  sortOrder?: string;
};
export type GetCustomerDetailApiV1AdminCustomersIdentityIdGetApiResponse =
  /** status 200 Successful Response */ CustomerDetailResponse;
export type GetCustomerDetailApiV1AdminCustomersIdentityIdGetApiArg = {
  identityId: string;
};
export type DeactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type DeactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePostApiArg = {
  identityId: string;
  adminDeactivateRequest: AdminDeactivateRequest;
};
export type ReactivateCustomerApiV1AdminCustomersIdentityIdReactivatePostApiResponse =
  /** status 200 Successful Response */ MessageResponse;
export type ReactivateCustomerApiV1AdminCustomersIdentityIdReactivatePostApiArg = {
  identityId: string;
};
export type CreateSupplierApiV1AdminSuppliersPostApiResponse =
  /** status 201 Successful Response */ SupplierCreateResponse;
export type CreateSupplierApiV1AdminSuppliersPostApiArg = {
  supplierCreateRequest: SupplierCreateRequest;
};
export type ListSuppliersApiV1AdminSuppliersGetApiResponse =
  /** status 200 Successful Response */ SupplierListResponse;
export type ListSuppliersApiV1AdminSuppliersGetApiArg = {
  offset?: number;
  limit?: number;
};
export type GetSupplierApiV1AdminSuppliersSupplierIdGetApiResponse =
  /** status 200 Successful Response */ SupplierResponse;
export type GetSupplierApiV1AdminSuppliersSupplierIdGetApiArg = {
  supplierId: string;
};
export type UpdateSupplierApiV1AdminSuppliersSupplierIdPutApiResponse = unknown;
export type UpdateSupplierApiV1AdminSuppliersSupplierIdPutApiArg = {
  supplierId: string;
  supplierUpdateRequest: SupplierUpdateRequest;
};
export type DeactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatchApiResponse = unknown;
export type DeactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatchApiArg = {
  supplierId: string;
};
export type ActivateSupplierApiV1AdminSuppliersSupplierIdActivatePatchApiResponse = unknown;
export type ActivateSupplierApiV1AdminSuppliersSupplierIdActivatePatchApiArg = {
  supplierId: string;
};
export type GetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetApiResponse =
  /** status 200 Successful Response */ StorefrontFilterListResponse;
export type GetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetApiArg = {
  categoryId: string;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type GetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetApiResponse =
  /** status 200 Successful Response */ StorefrontCardResponse;
export type GetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetApiArg = {
  categoryId: string;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type GetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetApiResponse =
  /** status 200 Successful Response */ StorefrontComparisonResponse;
export type GetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetApiArg =
  {
    categoryId: string;
    /** Locale code for i18n projection (e.g. 'ru', 'en') */
    lang?: string | null;
  };
export type GetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetApiResponse =
  /** status 200 Successful Response */ StorefrontFormResponse;
export type GetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetApiArg = {
  categoryId: string;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type StorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetApiResponse =
  /** status 200 Successful Response */ CategoryTreeResponse[];
export type StorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetApiArg = {
  maxDepth?: number | null;
};
export type StorefrontListCategoriesApiV1StorefrontCategoriesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseCategoryResponseRead;
export type StorefrontListCategoriesApiV1StorefrontCategoriesGetApiArg = {
  offset?: number;
  limit?: number;
};
export type StorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetApiResponse =
  /** status 200 Successful Response */ CategoryResponse;
export type StorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetApiArg = {
  categoryId: string;
};
export type StorefrontListBrandsApiV1StorefrontBrandsGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseBrandResponseRead;
export type StorefrontListBrandsApiV1StorefrontBrandsGetApiArg = {
  offset?: number;
  limit?: number;
};
export type StorefrontGetBrandApiV1StorefrontBrandsBrandIdGetApiResponse =
  /** status 200 Successful Response */ BrandResponse;
export type StorefrontGetBrandApiV1StorefrontBrandsBrandIdGetApiArg = {
  brandId: string;
};
export type ListStorefrontProductsApiV1StorefrontProductsGetApiResponse =
  /** status 200 Successful Response */ StorefrontPlpResponse;
export type ListStorefrontProductsApiV1StorefrontProductsGetApiArg = {
  /** Category to browse */
  categoryId: string;
  /** Filter by brand IDs (OR semantics) */
  brandId?: string[] | null;
  /** Min price (smallest currency unit) */
  priceMin?: number | null;
  /** Max price (smallest currency unit) */
  priceMax?: number | null;
  /** Only show in-stock products */
  inStock?: boolean | null;
  /** Sort order */
  sort?: string;
  /** Page size */
  limit?: number;
  /** Opaque pagination cursor */
  cursor?: string | null;
  /** Include total count (slower) */
  includeTotal?: boolean;
  /** Include facet counts for the filter panel */
  includeFacets?: boolean;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type GetStorefrontProductApiV1StorefrontProductsSlugGetApiResponse =
  /** status 200 Successful Response */ StorefrontProductDetailResponse;
export type GetStorefrontProductApiV1StorefrontProductsSlugGetApiArg = {
  slug: string;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type GetSimilarProductsApiV1StorefrontProductsSlugSimilarGetApiResponse =
  /** status 200 Successful Response */ StorefrontProductCardResponse[];
export type GetSimilarProductsApiV1StorefrontProductsSlugSimilarGetApiArg = {
  slug: string;
  /** Max number of cards */
  limit?: number;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type GetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetApiResponse =
  /** status 200 Successful Response */ StorefrontProductCardResponse[];
export type GetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetApiArg = {
  slug: string;
  /** Max number of cards */
  limit?: number;
  /** Locale code for i18n projection (e.g. 'ru', 'en') */
  lang?: string | null;
};
export type SearchProductsApiV1StorefrontSearchGetApiResponse =
  /** status 200 Successful Response */ StorefrontPlpResponse;
export type SearchProductsApiV1StorefrontSearchGetApiArg = {
  /** Search query text */
  q: string;
  /** Optional: scope search to a category */
  categoryId?: string | null;
  /** Filter by brand IDs (OR semantics) */
  brandId?: string[] | null;
  /** Min price (smallest currency unit) */
  priceMin?: number | null;
  /** Max price (smallest currency unit) */
  priceMax?: number | null;
  /** Only show in-stock products */
  inStock?: boolean | null;
  /** Sort order (relevant = FTS rank) */
  sort?: string;
  /** Page size */
  limit?: number;
  /** Opaque pagination cursor */
  cursor?: string | null;
  /** Include total count (slower) */
  includeTotal?: boolean;
  /** Include facet counts (requires categoryId) */
  includeFacets?: boolean;
  /** Locale code for i18n projection */
  lang?: string | null;
};
export type SearchSuggestApiV1StorefrontSearchSuggestGetApiResponse =
  /** status 200 Successful Response */ SearchSuggestionResponse[];
export type SearchSuggestApiV1StorefrontSearchSuggestGetApiArg = {
  /** Search prefix (min 2 chars) */
  q: string;
  /** Max suggestions to return */
  limit?: number;
  /** Preferred locale for suggestion text */
  lang?: string | null;
};
export type ListTrendingProductsApiV1StorefrontTrendingGetApiResponse =
  /** status 200 Successful Response */ StorefrontPlpResponse;
export type ListTrendingProductsApiV1StorefrontTrendingGetApiArg = {
  /** Maximum number of cards */
  limit?: number;
  /** Ranking window (ignored when category_id is set) */
  window?: string;
  /** Optional: scope trending to a category */
  categoryId?: string | null;
  /** Language for title projection */
  lang?: string | null;
};
export type GetForYouFeedApiV1StorefrontForYouGetApiResponse =
  /** status 200 Successful Response */ ForYouFeedResponse;
export type GetForYouFeedApiV1StorefrontForYouGetApiArg = {
  /** Page size */
  limit?: number;
  /** Opaque pagination token from a prior response. */
  cursor?: string | null;
  /** Language for title projection */
  lang?: string | null;
};
export type CreateBrandApiV1AdminCatalogBrandsPostApiResponse =
  /** status 201 Successful Response */ BrandCreateResponse;
export type CreateBrandApiV1AdminCatalogBrandsPostApiArg = {
  brandCreateRequest: BrandCreateRequest;
};
export type ListBrandsApiV1AdminCatalogBrandsGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseBrandResponseRead;
export type ListBrandsApiV1AdminCatalogBrandsGetApiArg = {
  offset?: number;
  limit?: number;
};
export type BulkCreateBrandsApiV1AdminCatalogBrandsBulkPostApiResponse =
  /** status 201 Successful Response */ BulkCreateBrandsResponse;
export type BulkCreateBrandsApiV1AdminCatalogBrandsBulkPostApiArg = {
  bulkCreateBrandsRequest: BulkCreateBrandsRequest;
};
export type GetBrandApiV1AdminCatalogBrandsBrandIdGetApiResponse =
  /** status 200 Successful Response */ BrandResponse;
export type GetBrandApiV1AdminCatalogBrandsBrandIdGetApiArg = {
  brandId: string;
};
export type UpdateBrandApiV1AdminCatalogBrandsBrandIdPatchApiResponse =
  /** status 200 Successful Response */ BrandResponse;
export type UpdateBrandApiV1AdminCatalogBrandsBrandIdPatchApiArg = {
  brandId: string;
  'If-Match'?: string | null;
  brandUpdateRequest: BrandUpdateRequest;
};
export type DeleteBrandApiV1AdminCatalogBrandsBrandIdDeleteApiResponse = unknown;
export type DeleteBrandApiV1AdminCatalogBrandsBrandIdDeleteApiArg = {
  brandId: string;
};
export type CreateCategoryApiV1AdminCatalogCategoriesPostApiResponse =
  /** status 201 Successful Response */ CategoryCreateResponse;
export type CreateCategoryApiV1AdminCatalogCategoriesPostApiArg = {
  categoryCreateRequest: CategoryCreateRequest;
};
export type ListCategoriesApiV1AdminCatalogCategoriesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseCategoryResponseRead;
export type ListCategoriesApiV1AdminCatalogCategoriesGetApiArg = {
  offset?: number;
  limit?: number;
};
export type BulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPostApiResponse =
  /** status 201 Successful Response */ BulkCreateCategoriesResponse;
export type BulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPostApiArg = {
  bulkCreateCategoriesRequest: BulkCreateCategoriesRequest;
};
export type GetCategoryTreeApiV1AdminCatalogCategoriesTreeGetApiResponse =
  /** status 200 Successful Response */ CategoryTreeResponse[];
export type GetCategoryTreeApiV1AdminCatalogCategoriesTreeGetApiArg = {
  /** Maximum tree depth to return */
  maxDepth?: number | null;
};
export type GetCategoryApiV1AdminCatalogCategoriesCategoryIdGetApiResponse =
  /** status 200 Successful Response */ CategoryResponse;
export type GetCategoryApiV1AdminCatalogCategoriesCategoryIdGetApiArg = {
  categoryId: string;
};
export type UpdateCategoryApiV1AdminCatalogCategoriesCategoryIdPatchApiResponse =
  /** status 200 Successful Response */ CategoryResponse;
export type UpdateCategoryApiV1AdminCatalogCategoriesCategoryIdPatchApiArg = {
  categoryId: string;
  'If-Match'?: string | null;
  categoryUpdateRequest: CategoryUpdateRequest;
};
export type DeleteCategoryApiV1AdminCatalogCategoriesCategoryIdDeleteApiResponse = unknown;
export type DeleteCategoryApiV1AdminCatalogCategoriesCategoryIdDeleteApiArg = {
  categoryId: string;
};
export type CreateAttributeApiV1AdminCatalogAttributesPostApiResponse =
  /** status 201 Successful Response */ AttributeCreateResponse;
export type CreateAttributeApiV1AdminCatalogAttributesPostApiArg = {
  attributeCreateRequest: AttributeCreateRequest;
};
export type ListAttributesApiV1AdminCatalogAttributesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseAttributeResponseRead;
export type ListAttributesApiV1AdminCatalogAttributesGetApiArg = {
  offset?: number;
  limit?: number;
  dataType?: string | null;
  uiType?: string | null;
  isDictionary?: boolean | null;
  groupId?: string | null;
  level?: string | null;
  isFilterable?: boolean | null;
  isSearchable?: boolean | null;
  isComparable?: boolean | null;
  search?: string | null;
};
export type BulkCreateAttributesApiV1AdminCatalogAttributesBulkPostApiResponse =
  /** status 201 Successful Response */ BulkCreateAttributesResponse;
export type BulkCreateAttributesApiV1AdminCatalogAttributesBulkPostApiArg = {
  bulkCreateAttributesRequest: BulkCreateAttributesRequest;
};
export type GetAttributeApiV1AdminCatalogAttributesAttributeIdGetApiResponse =
  /** status 200 Successful Response */ AttributeResponseRead;
export type GetAttributeApiV1AdminCatalogAttributesAttributeIdGetApiArg = {
  attributeId: string;
};
export type UpdateAttributeApiV1AdminCatalogAttributesAttributeIdPatchApiResponse =
  /** status 200 Successful Response */ AttributeResponseRead;
export type UpdateAttributeApiV1AdminCatalogAttributesAttributeIdPatchApiArg = {
  attributeId: string;
  attributeUpdateRequest: AttributeUpdateRequest;
};
export type DeleteAttributeApiV1AdminCatalogAttributesAttributeIdDeleteApiResponse = unknown;
export type DeleteAttributeApiV1AdminCatalogAttributesAttributeIdDeleteApiArg = {
  attributeId: string;
};
export type GetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetApiResponse =
  /** status 200 Successful Response */ AttributeUsageResponse;
export type GetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetApiArg = {
  attributeId: string;
};
export type CreateAttributeGroupApiV1AdminCatalogAttributeGroupsPostApiResponse =
  /** status 201 Successful Response */ AttributeGroupCreateResponse;
export type CreateAttributeGroupApiV1AdminCatalogAttributeGroupsPostApiArg = {
  attributeGroupCreateRequest: AttributeGroupCreateRequest;
};
export type ListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseAttributeGroupResponseRead;
export type ListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetApiArg = {
  offset?: number;
  limit?: number;
};
export type GetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetApiResponse =
  /** status 200 Successful Response */ AttributeGroupResponse;
export type GetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetApiArg = {
  groupId: string;
};
export type UpdateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatchApiResponse =
  /** status 200 Successful Response */ AttributeGroupResponse;
export type UpdateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatchApiArg = {
  groupId: string;
  attributeGroupUpdateRequest: AttributeGroupUpdateRequest;
};
export type DeleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDeleteApiResponse = unknown;
export type DeleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDeleteApiArg = {
  groupId: string;
};
export type AddAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPostApiResponse =
  /** status 201 Successful Response */ AttributeValueCreateResponse;
export type AddAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPostApiArg = {
  attributeId: string;
  attributeValueCreateRequest: AttributeValueCreateRequest;
};
export type ListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseAttributeValueResponseRead;
export type ListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetApiArg = {
  attributeId: string;
  offset?: number;
  limit?: number;
  search?: string | null;
};
export type BulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPostApiResponse =
  /** status 201 Successful Response */ BulkAddAttributeValuesResponse;
export type BulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPostApiArg = {
  attributeId: string;
  bulkAddAttributeValuesRequest: BulkAddAttributeValuesRequest;
};
export type GetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetApiResponse =
  /** status 200 Successful Response */ AttributeValueResponseRead;
export type GetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetApiArg = {
  attributeId: string;
  valueId: string;
};
export type UpdateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatchApiResponse =
  /** status 200 Successful Response */ AttributeValueResponseRead;
export type UpdateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatchApiArg = {
  attributeId: string;
  valueId: string;
  attributeValueUpdateRequest: AttributeValueUpdateRequest;
};
export type DeleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeleteApiResponse =
  unknown;
export type DeleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeleteApiArg = {
  attributeId: string;
  valueId: string;
};
export type DeactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatchApiResponse =
  /** status 200 Successful Response */ AttributeValueActiveResponse;
export type DeactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatchApiArg =
  {
    attributeId: string;
    valueId: string;
  };
export type ActivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatchApiResponse =
  /** status 200 Successful Response */ AttributeValueActiveResponse;
export type ActivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatchApiArg = {
  attributeId: string;
  valueId: string;
};
export type ReorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPostApiResponse =
  unknown;
export type ReorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPostApiArg = {
  attributeId: string;
  reorderAttributeValuesRequest: ReorderAttributeValuesRequest;
};
export type CreateTemplateApiV1AdminCatalogAttributeTemplatesPostApiResponse =
  /** status 201 Successful Response */ AttributeTemplateCreateResponse;
export type CreateTemplateApiV1AdminCatalogAttributeTemplatesPostApiArg = {
  attributeTemplateCreateRequest: AttributeTemplateCreateRequest;
};
export type ListTemplatesApiV1AdminCatalogAttributeTemplatesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseAttributeTemplateResponseRead;
export type ListTemplatesApiV1AdminCatalogAttributeTemplatesGetApiArg = {
  offset?: number;
  limit?: number;
};
export type CloneTemplateApiV1AdminCatalogAttributeTemplatesClonePostApiResponse =
  /** status 201 Successful Response */ CloneAttributeTemplateResponse;
export type CloneTemplateApiV1AdminCatalogAttributeTemplatesClonePostApiArg = {
  cloneAttributeTemplateRequest: CloneAttributeTemplateRequest;
};
export type GetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetApiResponse =
  /** status 200 Successful Response */ AttributeTemplateResponseRead;
export type GetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetApiArg = {
  templateId: string;
};
export type UpdateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatchApiResponse =
  /** status 200 Successful Response */ AttributeTemplateResponseRead;
export type UpdateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatchApiArg = {
  templateId: string;
  attributeTemplateUpdateRequest: AttributeTemplateUpdateRequest;
};
export type DeleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDeleteApiResponse = unknown;
export type DeleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDeleteApiArg = {
  templateId: string;
};
export type BindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPostApiResponse =
  /** status 201 Successful Response */ TemplateAttributeBindingEnrichedResponse;
export type BindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPostApiArg = {
  templateId: string;
  templateAttributeBindingRequest: TemplateAttributeBindingRequest;
};
export type ListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseTemplateAttributeBindingDetailResponseRead;
export type ListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetApiArg = {
  templateId: string;
  offset?: number;
  limit?: number;
};
export type UpdateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatchApiResponse =
  /** status 200 Successful Response */ TemplateAttributeBindingDetailResponse;
export type UpdateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatchApiArg =
  {
    templateId: string;
    bindingId: string;
    templateAttributeBindingUpdateRequest: TemplateAttributeBindingUpdateRequest;
  };
export type UnbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDeleteApiResponse =
  unknown;
export type UnbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDeleteApiArg =
  {
    templateId: string;
    bindingId: string;
  };
export type ReorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPostApiResponse =
  unknown;
export type ReorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPostApiArg =
  {
    templateId: string;
    templateBindingReorderRequest: TemplateBindingReorderRequest;
  };
export type CreateProductApiV1AdminCatalogProductsPostApiResponse =
  /** status 201 Successful Response */ ProductCreateResponse;
export type CreateProductApiV1AdminCatalogProductsPostApiArg = {
  productCreateRequest: ProductCreateRequest;
};
export type ListProductsApiV1AdminCatalogProductsGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseProductListItemResponseRead;
export type ListProductsApiV1AdminCatalogProductsGetApiArg = {
  offset?: number;
  limit?: number;
  status?: string | null;
  brandId?: string | null;
  /** Sort order: newest, oldest, popularity, name_asc, name_desc */
  sortBy?: string | null;
  /** Only include products published on or after this timestamp */
  publishedAfter?: string | null;
};
export type GetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetApiResponse =
  /** status 200 Successful Response */ ProductCompletenessResponse;
export type GetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetApiArg = {
  productId: string;
};
export type GetProductApiV1AdminCatalogProductsProductIdGetApiResponse =
  /** status 200 Successful Response */ ProductResponse;
export type GetProductApiV1AdminCatalogProductsProductIdGetApiArg = {
  productId: string;
};
export type UpdateProductApiV1AdminCatalogProductsProductIdPatchApiResponse =
  /** status 200 Successful Response */ ProductResponse;
export type UpdateProductApiV1AdminCatalogProductsProductIdPatchApiArg = {
  productId: string;
  'If-Match'?: string | null;
  productUpdateRequest: ProductUpdateRequest;
};
export type DeleteProductApiV1AdminCatalogProductsProductIdDeleteApiResponse = unknown;
export type DeleteProductApiV1AdminCatalogProductsProductIdDeleteApiArg = {
  productId: string;
};
export type StreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetApiResponse =
  /** status 200 Successful Response */ string;
export type StreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetApiArg = {
  productId: string;
};
export type BulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePostApiResponse =
  /** status 200 Successful Response */ BulkPurchasePriceResponse;
export type BulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePostApiArg =
  {
    productId: string;
    bulkPurchasePriceRequest: BulkPurchasePriceRequest;
  };
export type ChangeProductStatusApiV1AdminCatalogProductsProductIdStatusPatchApiResponse =
  /** status 200 Successful Response */ ProductResponse;
export type ChangeProductStatusApiV1AdminCatalogProductsProductIdStatusPatchApiArg = {
  productId: string;
  productStatusChangeRequest: ProductStatusChangeRequest;
};
export type ValidateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePostApiResponse =
  /** status 200 Successful Response */ ValidateUpdateResponse;
export type ValidateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePostApiArg = {
  productId: string;
  productUpdateRequest: ProductUpdateRequest;
};
export type ValidateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPostApiResponse =
  /** status 200 Successful Response */ ValidatePublishResponse;
export type ValidateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPostApiArg = {
  productId: string;
};
export type AddVariantApiV1AdminCatalogProductsProductIdVariantsPostApiResponse =
  /** status 201 Successful Response */ ProductVariantCreateResponse;
export type AddVariantApiV1AdminCatalogProductsProductIdVariantsPostApiArg = {
  productId: string;
  productVariantCreateRequest: ProductVariantCreateRequest;
};
export type ListVariantsApiV1AdminCatalogProductsProductIdVariantsGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseProductVariantResponseRead;
export type ListVariantsApiV1AdminCatalogProductsProductIdVariantsGetApiArg = {
  productId: string;
  limit?: number;
  offset?: number;
};
export type UpdateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatchApiResponse =
  /** status 200 Successful Response */ ProductVariantUpdateResponse;
export type UpdateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatchApiArg = {
  productId: string;
  variantId: string;
  'If-Match'?: string | null;
  productVariantUpdateRequest: ProductVariantUpdateRequest;
};
export type DeleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDeleteApiResponse =
  unknown;
export type DeleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDeleteApiArg = {
  productId: string;
  variantId: string;
};
export type AddSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPostApiResponse =
  /** status 201 Successful Response */ SkuCreateResponse;
export type AddSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPostApiArg = {
  productId: string;
  variantId: string;
  skuCreateRequest: SkuCreateRequest;
};
export type ListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseSkuResponseRead;
export type ListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetApiArg = {
  productId: string;
  variantId: string;
  limit?: number;
  offset?: number;
};
export type GenerateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePostApiResponse =
  /** status 201 Successful Response */ SkuMatrixGenerateResponse;
export type GenerateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePostApiArg =
  {
    productId: string;
    variantId: string;
    skuMatrixGenerateRequest: SkuMatrixGenerateRequest;
  };
export type UpdateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatchApiResponse =
  /** status 200 Successful Response */ SkuResponse;
export type UpdateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatchApiArg = {
  productId: string;
  variantId: string;
  skuId: string;
  'If-Match'?: string | null;
  skuUpdateRequest: SkuUpdateRequest;
};
export type DeleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDeleteApiResponse =
  unknown;
export type DeleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDeleteApiArg = {
  productId: string;
  variantId: string;
  skuId: string;
};
export type AssignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPostApiResponse =
  /** status 201 Successful Response */ ProductAttributeAssignResponse;
export type AssignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPostApiArg = {
  productId: string;
  productAttributeAssignRequest: ProductAttributeAssignRequest;
};
export type ListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseProductAttributeResponseRead;
export type ListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetApiArg = {
  productId: string;
  limit?: number;
  offset?: number;
};
export type BulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPostApiResponse =
  /** status 201 Successful Response */ BulkAssignProductAttributesResponse;
export type BulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPostApiArg =
  {
    productId: string;
    bulkAssignProductAttributesRequest: BulkAssignProductAttributesRequest;
  };
export type DeleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDeleteApiResponse =
  unknown;
export type DeleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDeleteApiArg =
  {
    productId: string;
    attributeId: string;
  };
export type AddProductMediaApiV1AdminCatalogProductsProductIdMediaPostApiResponse =
  /** status 201 Successful Response */ MediaAssetCreateResponse;
export type AddProductMediaApiV1AdminCatalogProductsProductIdMediaPostApiArg = {
  productId: string;
  mediaAssetCreateRequest: MediaAssetCreateRequest;
};
export type ListProductMediaApiV1AdminCatalogProductsProductIdMediaGetApiResponse =
  /** status 200 Successful Response */ PaginatedResponseMediaAssetResponseRead;
export type ListProductMediaApiV1AdminCatalogProductsProductIdMediaGetApiArg = {
  productId: string;
  offset?: number;
  limit?: number;
};
export type UpdateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatchApiResponse =
  /** status 200 Successful Response */ MediaAssetUpdateResponse;
export type UpdateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatchApiArg = {
  productId: string;
  mediaId: string;
  mediaAssetUpdateRequest: MediaAssetUpdateRequest;
};
export type DeleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDeleteApiResponse =
  unknown;
export type DeleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDeleteApiArg = {
  productId: string;
  mediaId: string;
};
export type ReorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPostApiResponse =
  unknown;
export type ReorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPostApiArg = {
  productId: string;
  mediaAssetReorderRequest: MediaAssetReorderRequest;
};
export type ListVariablesApiV1AdminPricingVariablesGetApiResponse =
  /** status 200 Successful Response */ VariableListResponse;
export type ListVariablesApiV1AdminPricingVariablesGetApiArg = {
  scope?: VariableScope | null;
  isSystem?: boolean | null;
  isFxRate?: boolean | null;
};
export type CreateVariableApiV1AdminPricingVariablesPostApiResponse =
  /** status 201 Successful Response */ CreateVariableResponse;
export type CreateVariableApiV1AdminPricingVariablesPostApiArg = {
  createVariableRequest: CreateVariableRequest;
};
export type GetVariableApiV1AdminPricingVariablesVariableIdGetApiResponse =
  /** status 200 Successful Response */ VariableResponse;
export type GetVariableApiV1AdminPricingVariablesVariableIdGetApiArg = {
  variableId: string;
};
export type UpdateVariableApiV1AdminPricingVariablesVariableIdPatchApiResponse =
  /** status 200 Successful Response */ VariableResponse;
export type UpdateVariableApiV1AdminPricingVariablesVariableIdPatchApiArg = {
  variableId: string;
  updateVariableRequest: UpdateVariableRequest;
};
export type DeleteVariableApiV1AdminPricingVariablesVariableIdDeleteApiResponse = unknown;
export type DeleteVariableApiV1AdminPricingVariablesVariableIdDeleteApiArg = {
  variableId: string;
};
export type ListContextsApiV1AdminPricingContextsGetApiResponse =
  /** status 200 Successful Response */ ContextListResponse;
export type ListContextsApiV1AdminPricingContextsGetApiArg = {
  isActive?: boolean | null;
  isFrozen?: boolean | null;
};
export type CreateContextApiV1AdminPricingContextsPostApiResponse =
  /** status 201 Successful Response */ CreateContextResponse;
export type CreateContextApiV1AdminPricingContextsPostApiArg = {
  createContextRequest: CreateContextRequest;
};
export type GetContextApiV1AdminPricingContextsContextIdGetApiResponse =
  /** status 200 Successful Response */ PricingContextResponse;
export type GetContextApiV1AdminPricingContextsContextIdGetApiArg = {
  contextId: string;
};
export type UpdateContextApiV1AdminPricingContextsContextIdPatchApiResponse =
  /** status 200 Successful Response */ PricingContextResponse;
export type UpdateContextApiV1AdminPricingContextsContextIdPatchApiArg = {
  contextId: string;
  updateContextRequest: UpdateContextRequest;
};
export type DeactivateContextApiV1AdminPricingContextsContextIdDeleteApiResponse =
  /** status 200 Successful Response */ MutateContextResponse;
export type DeactivateContextApiV1AdminPricingContextsContextIdDeleteApiArg = {
  contextId: string;
};
export type FreezeContextApiV1AdminPricingContextsContextIdFreezePostApiResponse =
  /** status 200 Successful Response */ MutateContextResponse;
export type FreezeContextApiV1AdminPricingContextsContextIdFreezePostApiArg = {
  contextId: string;
  freezeContextRequest: FreezeContextRequest;
};
export type UnfreezeContextApiV1AdminPricingContextsContextIdUnfreezePostApiResponse =
  /** status 200 Successful Response */ MutateContextResponse;
export type UnfreezeContextApiV1AdminPricingContextsContextIdUnfreezePostApiArg = {
  contextId: string;
};
export type GetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetApiResponse =
  /** status 200 Successful Response */ ContextGlobalValuesResponse;
export type GetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetApiArg = {
  contextId: string;
};
export type SetContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePutApiResponse =
  /** status 200 Successful Response */ SetContextGlobalValueResponse;
export type SetContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePutApiArg =
  {
    contextId: string;
    variableCode: string;
    setContextGlobalValueRequest: SetContextGlobalValueRequest;
  };
export type ListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetApiResponse =
  /** status 200 Successful Response */ FormulaVersionListResponse;
export type ListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetApiArg = {
  contextId: string;
  status?: FormulaStatus | null;
};
export type GetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetApiResponse =
  /** status 200 Successful Response */ FormulaVersionResponse;
export type GetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetApiArg = {
  contextId: string;
  versionId: string;
};
export type GetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetApiResponse =
  /** status 200 Successful Response */ FormulaVersionResponse;
export type GetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetApiArg = {
  contextId: string;
};
export type UpsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPutApiResponse =
  /** status 200 Successful Response */ UpsertFormulaDraftResponse;
export type UpsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPutApiArg = {
  contextId: string;
  upsertFormulaDraftRequest: UpsertFormulaDraftRequest;
};
export type DiscardDraftApiV1AdminPricingContextsContextIdFormulaDraftDeleteApiResponse =
  /** status 200 Successful Response */ DiscardFormulaDraftResponse;
export type DiscardDraftApiV1AdminPricingContextsContextIdFormulaDraftDeleteApiArg = {
  contextId: string;
};
export type PublishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPostApiResponse =
  /** status 200 Successful Response */ PublishFormulaResponse;
export type PublishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPostApiArg = {
  contextId: string;
};
export type RollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPostApiResponse =
  /** status 200 Successful Response */ RollbackFormulaResponse;
export type RollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPostApiArg =
  {
    contextId: string;
    versionId: string;
  };
export type PreviewPriceApiV1AdminPricingPreviewPostApiResponse =
  /** status 200 Successful Response */ PreviewPriceResponse;
export type PreviewPriceApiV1AdminPricingPreviewPostApiArg = {
  previewPriceRequest: PreviewPriceRequest;
};
export type PreviewSkuPricingApiV1AdminPricingPreviewSkuPostApiResponse =
  /** status 200 Successful Response */ PreviewSkuPricingResponse;
export type PreviewSkuPricingApiV1AdminPricingPreviewSkuPostApiArg = {
  previewSkuPricingRequest: PreviewSkuPricingRequest;
};
export type GetProfileApiV1AdminPricingProductsProductIdProfileGetApiResponse =
  /** status 200 Successful Response */ ProductPricingProfileResponse;
export type GetProfileApiV1AdminPricingProductsProductIdProfileGetApiArg = {
  productId: string;
};
export type UpsertProfileApiV1AdminPricingProductsProductIdProfilePutApiResponse =
  /** status 200 Successful Response */ UpsertProductPricingProfileResponse;
export type UpsertProfileApiV1AdminPricingProductsProductIdProfilePutApiArg = {
  productId: string;
  upsertProductPricingProfileRequest: UpsertProductPricingProfileRequest;
};
export type DeleteProfileApiV1AdminPricingProductsProductIdProfileDeleteApiResponse = unknown;
export type DeleteProfileApiV1AdminPricingProductsProductIdProfileDeleteApiArg = {
  productId: string;
};
export type GetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetApiResponse =
  /** status 200 Successful Response */ RequiredVariablesResponse;
export type GetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetApiArg =
  {
    productId: string;
  };
export type GetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetApiResponse =
  /** status 200 Successful Response */ SupplierPricingSettingsResponse;
export type GetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetApiArg = {
  supplierId: string;
};
export type UpsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPutApiResponse =
  /** status 200 Successful Response */ UpsertSupplierPricingSettingsResponse;
export type UpsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPutApiArg = {
  supplierId: string;
  upsertSupplierPricingSettingsRequest: UpsertSupplierPricingSettingsRequest;
};
export type ListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetApiResponse =
  /** status 200 Successful Response */ SupplierTypeContextMappingListResponse;
export type ListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetApiArg = void;
export type GetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetApiResponse =
  /** status 200 Successful Response */ SupplierTypeContextMappingResponse;
export type GetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetApiArg =
  {
    supplierType: string;
  };
export type UpsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePutApiResponse =
  /** status 200 Successful Response */ UpsertSupplierTypeContextMappingResponse;
export type UpsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePutApiArg =
  {
    supplierType: string;
    upsertSupplierTypeContextMappingRequest: UpsertSupplierTypeContextMappingRequest;
  };
export type DeleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDeleteApiResponse =
  unknown;
export type DeleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDeleteApiArg =
  {
    supplierType: string;
  };
export type GetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetApiResponse =
  /** status 200 Successful Response */ CategoryPricingSettingsResponse;
export type GetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetApiArg = {
  categoryId: string;
  /** Target pricing context id */
  contextId: string;
};
export type UpsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPutApiResponse =
  /** status 200 Successful Response */ UpsertCategoryPricingSettingsResponse;
export type UpsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPutApiArg = {
  categoryId: string;
  contextId: string;
  upsertCategoryPricingSettingsRequest: UpsertCategoryPricingSettingsRequest;
};
export type DeleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDeleteApiResponse =
  unknown;
export type DeleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDeleteApiArg =
  {
    categoryId: string;
    contextId: string;
  };
export type RecomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPostApiResponse =
  /** status 200 Successful Response */ RecomputeSkuResponse;
export type RecomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPostApiArg = {
  skuId: string;
};
export type RecomputeContextApiV1AdminPricingRecomputeContextsContextIdPostApiResponse =
  /** status 202 Successful Response */ RecomputeFanoutResponse;
export type RecomputeContextApiV1AdminPricingRecomputeContextsContextIdPostApiArg = {
  contextId: string;
};
export type RecomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPostApiResponse =
  /** status 202 Successful Response */ RecomputeFanoutResponse;
export type RecomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPostApiArg = {
  categoryId: string;
};
export type RecomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPostApiResponse =
  /** status 202 Successful Response */ RecomputeFanoutResponse;
export type RecomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPostApiArg = {
  supplierId: string;
};
export type GetTrendingProductsApiV1AdminAnalyticsTrendingGetApiResponse =
  /** status 200 Successful Response */ TrendingProductsResponse;
export type GetTrendingProductsApiV1AdminAnalyticsTrendingGetApiArg = {
  limit?: number;
  window?: string;
  categoryId?: string | null;
};
export type GetSearchAnalyticsApiV1AdminAnalyticsSearchGetApiResponse =
  /** status 200 Successful Response */ SearchAnalyticsResponse;
export type GetSearchAnalyticsApiV1AdminAnalyticsSearchGetApiArg = {
  limit?: number;
};
export type AddItemApiV1CartItemsPostApiResponse =
  /** status 201 Successful Response */ AddItemResponse;
export type AddItemApiV1CartItemsPostApiArg = {
  'x-anonymous-token'?: string | null;
  addItemRequest: AddItemRequest;
};
export type RemoveItemApiV1CartItemsSkuIdDeleteApiResponse = unknown;
export type RemoveItemApiV1CartItemsSkuIdDeleteApiArg = {
  skuId: string;
  'x-anonymous-token'?: string | null;
};
export type UpdateQuantityApiV1CartItemsSkuIdPatchApiResponse = unknown;
export type UpdateQuantityApiV1CartItemsSkuIdPatchApiArg = {
  skuId: string;
  'x-anonymous-token'?: string | null;
  updateQuantityRequest: UpdateQuantityRequest;
};
export type ClearCartApiV1CartDeleteApiResponse = unknown;
export type ClearCartApiV1CartDeleteApiArg = {
  'x-anonymous-token'?: string | null;
};
export type GetCartApiV1CartGetApiResponse = /** status 200 Successful Response */ CartResponse;
export type GetCartApiV1CartGetApiArg = {
  'x-anonymous-token'?: string | null;
};
export type GetCartSummaryApiV1CartSummaryGetApiResponse =
  /** status 200 Successful Response */ CartSummaryResponse;
export type GetCartSummaryApiV1CartSummaryGetApiArg = {
  'x-anonymous-token'?: string | null;
};
export type InitiateCheckoutApiV1CartCheckoutPostApiResponse =
  /** status 200 Successful Response */ CheckoutInitiatedResponse;
export type InitiateCheckoutApiV1CartCheckoutPostApiArg = {
  initiateCheckoutRequest: InitiateCheckoutRequest;
};
export type ConfirmCheckoutApiV1CartCheckoutConfirmPostApiResponse =
  /** status 200 Successful Response */ CheckoutConfirmedResponse;
export type ConfirmCheckoutApiV1CartCheckoutConfirmPostApiArg = {
  confirmCheckoutRequest: ConfirmCheckoutRequest;
};
export type CancelCheckoutApiV1CartCheckoutCancelPostApiResponse = unknown;
export type CancelCheckoutApiV1CartCheckoutCancelPostApiArg = void;
export type MergeCartsApiV1CartMergePostApiResponse = unknown;
export type MergeCartsApiV1CartMergePostApiArg = {
  mergeCartRequest: MergeCartRequest;
};
export type CreateAnonymousTokenApiV1CartAnonymousTokenPostApiResponse =
  /** status 201 Successful Response */ AnonymousTokenResponse;
export type CreateAnonymousTokenApiV1CartAnonymousTokenPostApiArg = void;
export type ListFavoriteListsApiV1FavoritesListsGetApiResponse =
  /** status 200 Successful Response */ FavoriteListsResponse;
export type ListFavoriteListsApiV1FavoritesListsGetApiArg = void;
export type CreateFavoriteListApiV1FavoritesListsPostApiResponse =
  /** status 201 Successful Response */ CreateFavoriteListResponse;
export type CreateFavoriteListApiV1FavoritesListsPostApiArg = {
  createFavoriteListRequest: CreateFavoriteListRequest;
};
export type RenameFavoriteListApiV1FavoritesListsListIdPatchApiResponse = unknown;
export type RenameFavoriteListApiV1FavoritesListsListIdPatchApiArg = {
  listId: string;
  renameFavoriteListRequest: RenameFavoriteListRequest;
};
export type DeleteFavoriteListApiV1FavoritesListsListIdDeleteApiResponse = unknown;
export type DeleteFavoriteListApiV1FavoritesListsListIdDeleteApiArg = {
  listId: string;
};
export type ListFavoriteItemsApiV1FavoritesListsListIdItemsGetApiResponse =
  /** status 200 Successful Response */ FavoriteItemsPageResponse;
export type ListFavoriteItemsApiV1FavoritesListsListIdItemsGetApiArg = {
  listId: string;
  targetType?: FavoriteTargetType | null;
  cursor?: string | null;
  limit?: number;
};
export type AddFavoriteItemApiV1FavoritesItemsPostApiResponse =
  /** status 201 Successful Response */ AddFavoriteItemResponse;
export type AddFavoriteItemApiV1FavoritesItemsPostApiArg = {
  addFavoriteItemRequest: AddFavoriteItemRequest;
};
export type RemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteApiResponse =
  unknown;
export type RemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteApiArg = {
  listId: string;
  targetType: FavoriteTargetType;
  targetId: string;
};
export type MoveFavoriteItemApiV1FavoritesItemsMovePostApiResponse = unknown;
export type MoveFavoriteItemApiV1FavoritesItemsMovePostApiArg = {
  moveFavoriteItemRequest: MoveFavoriteItemRequest;
};
export type CheckFavoritedApiV1FavoritesCheckPostApiResponse =
  /** status 200 Successful Response */ CheckFavoritedResponse;
export type CheckFavoritedApiV1FavoritesCheckPostApiArg = {
  checkFavoritedRequest: CheckFavoritedRequest;
};
export type RequestUploadApiV1AdminMediaUploadPostApiResponse =
  /** status 201 Successful Response */ UploadResponse;
export type RequestUploadApiV1AdminMediaUploadPostApiArg = {
  uploadRequest: UploadRequest;
};
export type ReuploadApiV1AdminMediaStorageObjectIdReuploadPostApiResponse =
  /** status 200 Successful Response */ ReuploadResponse;
export type ReuploadApiV1AdminMediaStorageObjectIdReuploadPostApiArg = {
  storageObjectId: string;
  reuploadRequest: ReuploadRequest;
};
export type ConfirmUploadApiV1AdminMediaStorageObjectIdConfirmPostApiResponse =
  /** status 202 Successful Response */ ConfirmResponse;
export type ConfirmUploadApiV1AdminMediaStorageObjectIdConfirmPostApiArg = {
  storageObjectId: string;
};
export type StreamStatusApiV1AdminMediaStorageObjectIdStatusGetApiResponse =
  /** status 200 Successful Response */ string;
export type StreamStatusApiV1AdminMediaStorageObjectIdStatusGetApiArg = {
  storageObjectId: string;
};
export type GetMetadataApiV1AdminMediaStorageObjectIdGetApiResponse =
  /** status 200 Successful Response */ MetadataResponse;
export type GetMetadataApiV1AdminMediaStorageObjectIdGetApiArg = {
  storageObjectId: string;
};
export type DeleteMediaApiV1AdminMediaStorageObjectIdDeleteApiResponse =
  /** status 200 Successful Response */ DeleteResponse;
export type DeleteMediaApiV1AdminMediaStorageObjectIdDeleteApiArg = {
  storageObjectId: string;
};
export type ImportExternalApiV1AdminMediaExternalPostApiResponse =
  /** status 201 Successful Response */ ExternalImportResponse;
export type ImportExternalApiV1AdminMediaExternalPostApiArg = {
  externalImportRequest: ExternalImportRequest;
};
export type RequestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPostApiResponse =
  /** status 202 Successful Response */ RemoveBackgroundResponse;
export type RequestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPostApiArg = {
  storageObjectId: string;
};
export type ListPickupPointsApiV1StorefrontLogisticsPickupPointsPostApiResponse =
  /** status 200 Successful Response */ PickupPointsResponse;
export type ListPickupPointsApiV1StorefrontLogisticsPickupPointsPostApiArg = {
  pickupPointsRequest: PickupPointsRequest;
};
export type ListProviderAccountsApiV1AdminLogisticsProviderAccountsGetApiResponse =
  /** status 200 Successful Response */ ProviderAccountListResponse;
export type ListProviderAccountsApiV1AdminLogisticsProviderAccountsGetApiArg = {
  providerCode?: string | null;
  onlyActive?: boolean;
};
export type CreateProviderAccountApiV1AdminLogisticsProviderAccountsPostApiResponse =
  /** status 201 Successful Response */ ProviderAccountResponse;
export type CreateProviderAccountApiV1AdminLogisticsProviderAccountsPostApiArg = {
  createProviderAccountRequest: CreateProviderAccountRequest;
};
export type GetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetApiResponse =
  /** status 200 Successful Response */ ProviderAccountResponse;
export type GetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetApiArg = {
  accountId: string;
};
export type UpdateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPutApiResponse =
  /** status 200 Successful Response */ ProviderAccountResponse;
export type UpdateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPutApiArg = {
  accountId: string;
  updateProviderAccountRequest: UpdateProviderAccountRequest;
};
export type DeleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDeleteApiResponse =
  unknown;
export type DeleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDeleteApiArg = {
  accountId: string;
};
export type SetProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePostApiResponse =
  /** status 200 Successful Response */ ProviderAccountResponse;
export type SetProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePostApiArg = {
  accountId: string;
  setProviderAccountActiveRequest: SetProviderAccountActiveRequest;
};
export type RefreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPostApiResponse =
  /** status 200 Successful Response */ RefreshRegistryResponse;
export type RefreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPostApiArg = void;
export type CalculateRatesApiV1AdminLogisticsRatesPostApiResponse =
  /** status 200 Successful Response */ CalculateRatesResponse;
export type CalculateRatesApiV1AdminLogisticsRatesPostApiArg = {
  calculateRatesRequest: CalculateRatesRequest;
};
export type QuoteForPickupPointApiV1AdminLogisticsRatesQuotePostApiResponse =
  /** status 200 Successful Response */ RateQuoteResponse;
export type QuoteForPickupPointApiV1AdminLogisticsRatesQuotePostApiArg = {
  rateQuoteRequest: RateQuoteRequest;
};
export type ListAdminShipmentsApiV1AdminLogisticsShipmentsGetApiResponse =
  /** status 200 Successful Response */ AdminShipmentListResponse;
export type ListAdminShipmentsApiV1AdminLogisticsShipmentsGetApiArg = {
  /** Restrict to a single provider code. */
  provider?:
    | ('cdek' | 'yandex_delivery' | 'dobropost' | 'russian_post' | 'boxberry' | 'pochta')
    | null;
  /** Restrict to a single FSM state. */
  status?:
    | ('draft' | 'booking_pending' | 'booked' | 'cancel_pending' | 'cancelled' | 'failed')
    | null;
  /** Restrict to shipments linked to a specific order. */
  orderId?: string | null;
  /** Inclusive lower bound on ``created_at``. */
  createdAfter?: string | null;
  /** Exclusive upper bound on ``created_at``. */
  createdBefore?: string | null;
  /** Case-insensitive substring match on tracking_number. */
  trackingNumberContains?: string | null;
  /** Page size. */
  limit?: number;
  /** ``next_cursor`` from the previous response. */
  cursor?: string | null;
};
export type CreateShipmentApiV1AdminLogisticsShipmentsPostApiResponse =
  /** status 201 Successful Response */ ShipmentResponse;
export type CreateShipmentApiV1AdminLogisticsShipmentsPostApiArg = {
  createShipmentRequest: CreateShipmentRequest;
};
export type BookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPostApiResponse =
  /** status 200 Successful Response */ BookShipmentResponse;
export type BookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPostApiArg = {
  shipmentId: string;
};
export type CancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPostApiResponse =
  /** status 200 Successful Response */ CancelShipmentResponse;
export type CancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPostApiArg = {
  shipmentId: string;
};
export type GetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetApiResponse =
  /** status 200 Successful Response */ ShipmentResponse;
export type GetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetApiArg = {
  shipmentId: string;
};
export type GetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetApiResponse =
  /** status 200 Successful Response */ TrackingResponse;
export type GetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetApiArg = {
  shipmentId: string;
};
export type ListPickupPointsApiV1AdminLogisticsPickupPointsPostApiResponse =
  /** status 200 Successful Response */ PickupPointsResponse;
export type ListPickupPointsApiV1AdminLogisticsPickupPointsPostApiArg = {
  pickupPointsRequest: PickupPointsRequest;
};
export type ListAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPostApiResponse =
  /** status 200 Successful Response */ AvailableIntakeDaysResponse;
export type ListAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPostApiArg = {
  availableIntakeDaysRequest: AvailableIntakeDaysRequest;
};
export type CreateIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePostApiResponse =
  /** status 201 Successful Response */ CreateIntakeResponse;
export type CreateIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePostApiArg = {
  shipmentId: string;
  createIntakeRequest: CreateIntakeRequest;
};
export type GetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetApiResponse =
  /** status 200 Successful Response */ IntakeStatusResponse;
export type GetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetApiArg = {
  providerCode: string;
  providerIntakeId: string;
};
export type CancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDeleteApiResponse =
  /** status 200 Successful Response */ CancelIntakeResponse;
export type CancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDeleteApiArg = {
  providerCode: string;
  providerIntakeId: string;
  shipmentId?: string | null;
};
export type GetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetApiResponse =
  /** status 200 Successful Response */ DeliveryIntervalsResponse;
export type GetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetApiArg = {
  shipmentId: string;
};
export type EstimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePostApiResponse =
  /** status 200 Successful Response */ DeliveryIntervalsResponse;
export type EstimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePostApiArg = {
  estimatedDeliveryIntervalsRequest: EstimatedDeliveryIntervalsRequest;
};
export type RegisterClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPostApiResponse =
  /** status 201 Successful Response */ ReturnResponse;
export type RegisterClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPostApiArg = {
  shipmentId: string;
  clientReturnRequest: ClientReturnRequest;
};
export type RegisterRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPostApiResponse =
  /** status 201 Successful Response */ ReturnResponse;
export type RegisterRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPostApiArg = {
  shipmentId: string;
  refusalRequestSchema: RefusalRequestSchema;
};
export type CheckReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPostApiResponse =
  /** status 200 Successful Response */ ReverseAvailabilityResponse;
export type CheckReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPostApiArg = {
  reverseAvailabilityRequestSchema: ReverseAvailabilityRequestSchema;
};
export type GetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetApiResponse =
  /** status 200 Successful Response */ ActualDeliveryInfoResponse;
export type GetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetApiArg =
  {
    shipmentId: string;
  };
export type EditOrderApiV1AdminLogisticsShipmentsShipmentIdEditPostApiResponse =
  /** status 202 Successful Response */ EditTaskResponse;
export type EditOrderApiV1AdminLogisticsShipmentsShipmentIdEditPostApiArg = {
  shipmentId: string;
  editOrderRequest: EditOrderRequest;
};
export type EditOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPostApiResponse =
  /** status 202 Successful Response */ EditTaskResponse;
export type EditOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPostApiArg = {
  shipmentId: string;
  editPackagesRequest: EditPackagesRequest;
};
export type EditOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPostApiResponse =
  /** status 202 Successful Response */ EditTaskResponse;
export type EditOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPostApiArg = {
  shipmentId: string;
  editOrderItemsRequest: EditOrderItemsRequest;
};
export type RemoveOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPostApiResponse =
  /** status 202 Successful Response */ EditTaskResponse;
export type RemoveOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPostApiArg = {
  shipmentId: string;
  removeOrderItemsRequest: RemoveOrderItemsRequest;
};
export type GetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetApiResponse =
  /** status 200 Successful Response */ EditTaskStatusResponse;
export type GetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetApiArg = {
  providerCode: string;
  taskId: string;
};
export type EditCdekOrderApiV1AdminLogisticsCdekOrdersEditPostApiResponse =
  /** status 200 Successful Response */ CdekEditOrderResponse;
export type EditCdekOrderApiV1AdminLogisticsCdekOrdersEditPostApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type LookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type LookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetApiArg = {
  cdekNumber?: string | null;
  imNumber?: string | null;
};
export type ListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetApiArg = {
  orderUuid: string;
};
export type DownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetApiResponse =
  unknown;
export type DownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetApiArg = {
  shipmentId: string;
};
export type RegisterCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPostApiResponse =
  /** status 202 Successful Response */ CdekJsonResponse;
export type RegisterCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPostApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type GetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type GetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetApiArg =
  {
    agreementUuid: string;
  };
export type CreateCdekPrealertApiV1AdminLogisticsCdekPrealertsPostApiResponse =
  /** status 202 Successful Response */ CdekJsonResponse;
export type CreateCdekPrealertApiV1AdminLogisticsCdekPrealertsPostApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type GetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type GetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetApiArg = {
  prealertUuid: string;
};
export type GetCdekChecksApiV1AdminLogisticsCdekChecksGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type GetCdekChecksApiV1AdminLogisticsCdekChecksGetApiArg = {
  orderUuid?: string | null;
  cdekNumber?: string | null;
  date?: string | null;
};
export type GetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type GetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetApiArg = {
  /** Registry date, YYYY-MM-DD. */
  date: string;
};
export type CheckCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPostApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type CheckCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPostApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type GetCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPostApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type GetCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPostApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type ChangeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatchApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ChangeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatchApiArg = {
  cdekRawPayloadRequest: CdekRawPayloadRequest;
};
export type ListCdekTariffsApiV1AdminLogisticsCdekTariffsGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekTariffsApiV1AdminLogisticsCdekTariffsGetApiArg = void;
export type SuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type SuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetApiArg = {
  /** City name fragment. */
  name: string;
  countryCode?: string | null;
};
export type ListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetApiArg = {
  city?: string | null;
  countryCodes?: string | null;
  postalCode?: string | null;
  code?: number | null;
};
export type ListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetApiArg = {
  countryCodes?: string | null;
};
export type ListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetApiArg = {
  /** CDEK city code. */
  cityCode: number;
};
export type ResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetApiArg =
  {
    latitude: number;
    longitude: number;
  };
export type ListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetApiResponse =
  /** status 200 Successful Response */ CdekJsonResponse;
export type ListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetApiArg = void;
export type CreateCdekWebhookApiV1AdminLogisticsCdekWebhooksPostApiResponse =
  /** status 201 Successful Response */ CdekJsonResponse;
export type CreateCdekWebhookApiV1AdminLogisticsCdekWebhooksPostApiArg = {
  cdekWebhookSubscriptionRequest: CdekWebhookSubscriptionRequest;
};
export type SyncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPostApiResponse =
  /** status 200 Successful Response */ CdekWebhookSyncResponse;
export type SyncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPostApiArg = {
  cdekWebhookSyncRequest: CdekWebhookSyncRequest;
};
export type DeleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDeleteApiResponse =
  unknown;
export type DeleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDeleteApiArg = {
  subscriptionUuid: string;
};
export type ReceiveWebhookApiV1WebhooksLogisticsProviderCodePostApiResponse =
  /** status 200 Successful Response */ {
    [key: string]: any;
  };
export type ReceiveWebhookApiV1WebhooksLogisticsProviderCodePostApiArg = {
  providerCode: string;
};
export type GetPaymentIntentApiV1PaymentsIntentsIntentIdGetApiResponse =
  /** status 200 Successful Response */ PaymentIntentSchema;
export type GetPaymentIntentApiV1PaymentsIntentsIntentIdGetApiArg = {
  intentId: string;
};
export type SimulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePostApiResponse = unknown;
export type SimulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePostApiArg = {
  intentId: string;
  simulateCaptureRequest: SimulateCaptureRequest;
};
export type ProviderWebhookApiV1WebhooksPaymentsProviderPostApiResponse = unknown;
export type ProviderWebhookApiV1WebhooksPaymentsProviderPostApiArg = {
  provider: string;
  payload: {
    [key: string]: any;
  };
};
export type CreateRecipientApiV1RecipientsPostApiResponse =
  /** status 201 Successful Response */ CreateRecipientResponse;
export type CreateRecipientApiV1RecipientsPostApiArg = {
  createRecipientRequest: CreateRecipientRequest;
};
export type ListMyRecipientsApiV1RecipientsGetApiResponse =
  /** status 200 Successful Response */ RecipientListResponse;
export type ListMyRecipientsApiV1RecipientsGetApiArg = {
  includeArchived?: boolean;
};
export type GetRecipientApiV1RecipientsRecipientIdGetApiResponse =
  /** status 200 Successful Response */ RecipientSchema;
export type GetRecipientApiV1RecipientsRecipientIdGetApiArg = {
  recipientId: string;
};
export type UpdateRecipientApiV1RecipientsRecipientIdPatchApiResponse = unknown;
export type UpdateRecipientApiV1RecipientsRecipientIdPatchApiArg = {
  recipientId: string;
  'If-Match'?: string | null;
  updateRecipientRequest: UpdateRecipientRequest;
};
export type ArchiveRecipientApiV1RecipientsRecipientIdDeleteApiResponse = unknown;
export type ArchiveRecipientApiV1RecipientsRecipientIdDeleteApiArg = {
  recipientId: string;
};
export type CreateOrderApiV1OrdersPostApiResponse =
  /** status 201 Successful Response */ CreateOrderResponse;
export type CreateOrderApiV1OrdersPostApiArg = {
  createOrderRequest: CreateOrderRequest;
};
export type ListMyOrdersApiV1OrdersGetApiResponse =
  /** status 200 Successful Response */ CustomerOrderListResponse;
export type ListMyOrdersApiV1OrdersGetApiArg = {
  limit?: number;
  cursor?: string | null;
};
export type GetOrderApiV1OrdersOrderIdGetApiResponse =
  /** status 200 Successful Response */ CustomerOrderSchema;
export type GetOrderApiV1OrdersOrderIdGetApiArg = {
  orderId: string;
};
export type GetOrderTrackingApiV1OrdersOrderIdTrackingGetApiResponse =
  /** status 200 Successful Response */ OrderTrackingResponse;
export type GetOrderTrackingApiV1OrdersOrderIdTrackingGetApiArg = {
  orderId: string;
};
export type CancelOrderApiV1OrdersOrderIdCancelPostApiResponse = unknown;
export type CancelOrderApiV1OrdersOrderIdCancelPostApiArg = {
  orderId: string;
  cancelOrderRequest: CancelOrderRequest;
};
export type RefreshRecipientApiV1OrdersOrderIdRefreshRecipientPostApiResponse = unknown;
export type RefreshRecipientApiV1OrdersOrderIdRefreshRecipientPostApiArg = {
  orderId: string;
};
export type ChangePickupPointApiV1OrdersOrderIdPickupPointPatchApiResponse = unknown;
export type ChangePickupPointApiV1OrdersOrderIdPickupPointPatchApiArg = {
  orderId: string;
  changePickupPointRequest: ChangePickupPointRequest;
};
export type AdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetApiResponse =
  /** status 200 Successful Response */ CancellationReasonsMetaResponse;
export type AdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetApiArg = void;
export type AdminListOrdersApiV1AdminOrdersGetApiResponse =
  /** status 200 Successful Response */ AdminOrderListResponse;
export type AdminListOrdersApiV1AdminOrdersGetApiArg = {
  statuses?: string[] | null;
  limit?: number;
  cursor?: string | null;
};
export type AdminGetOrderApiV1AdminOrdersOrderIdGetApiResponse =
  /** status 200 Successful Response */ AdminOrderSchema;
export type AdminGetOrderApiV1AdminOrdersOrderIdGetApiArg = {
  orderId: string;
};
export type AdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetApiResponse =
  /** status 200 Successful Response */ OrderStateHistoryEntrySchema[];
export type AdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetApiArg = {
  orderId: string;
};
export type AdminProcureOrderApiV1AdminOrdersOrderIdProcurePostApiResponse = unknown;
export type AdminProcureOrderApiV1AdminOrdersOrderIdProcurePostApiArg = {
  orderId: string;
  procureOrderRequest: ProcureOrderRequest;
};
export type AdminHoldOrderApiV1AdminOrdersOrderIdHoldPostApiResponse = unknown;
export type AdminHoldOrderApiV1AdminOrdersOrderIdHoldPostApiArg = {
  orderId: string;
  holdOrderRequest: HoldOrderRequest;
};
export type AdminResumeOrderApiV1AdminOrdersOrderIdResumePostApiResponse = unknown;
export type AdminResumeOrderApiV1AdminOrdersOrderIdResumePostApiArg = {
  orderId: string;
};
export type AdminForceCancelApiV1AdminOrdersOrderIdForceCancelPostApiResponse = unknown;
export type AdminForceCancelApiV1AdminOrdersOrderIdForceCancelPostApiArg = {
  orderId: string;
  cancelOrderRequest: CancelOrderRequest;
};
export type AdminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatchApiResponse = unknown;
export type AdminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatchApiArg = {
  orderId: string;
  changePickupPointRequest: ChangePickupPointRequest;
};
export type DobropostWebhookApiV1WebhooksDobropostTokenPostApiResponse = unknown;
export type DobropostWebhookApiV1WebhooksDobropostTokenPostApiArg = {
  token: string;
  payload: {
    [key: string]: any;
  };
};
export type HealthCheckHealthGetApiResponse = /** status 200 Successful Response */ {
  [key: string]: string;
};
export type HealthCheckHealthGetApiArg = void;
export type CountryTranslationReadModel = {
  langCode: string;
  name: string;
  officialName?: string | null;
};
export type CountryReadModel = {
  alpha2: string;
  alpha3: string;
  numeric: string;
  translations?: CountryTranslationReadModel[];
};
export type CountryListReadModel = {
  items: CountryReadModel[];
  total: number;
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: any;
  ctx?: object;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type CurrencyTranslationReadModel = {
  langCode: string;
  name: string;
};
export type CurrencyReadModel = {
  code: string;
  numeric: string;
  name: string;
  minorUnit?: number | null;
  isActive?: boolean;
  sortOrder?: number;
  translations?: CurrencyTranslationReadModel[];
};
export type CurrencyListReadModel = {
  items: CurrencyReadModel[];
  total: number;
};
export type LanguageReadModel = {
  code: string;
  iso6391?: string | null;
  iso6392?: string | null;
  iso6393?: string | null;
  script?: string | null;
  nameEn: string;
  nameNative: string;
  direction: string;
  isActive: boolean;
  isDefault: boolean;
  sortOrder: number;
};
export type LanguageListReadModel = {
  items: LanguageReadModel[];
  total: number;
};
export type SubdivisionTranslationReadModel = {
  langCode: string;
  name: string;
  officialName?: string | null;
  localVariant?: string | null;
};
export type SubdivisionReadModel = {
  code: string;
  countryCode: string;
  typeCode: string;
  parentCode?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  isActive?: boolean;
  sortOrder?: number;
  translations?: SubdivisionTranslationReadModel[];
};
export type SubdivisionListReadModel = {
  items: SubdivisionReadModel[];
  total: number;
};
export type DistrictTranslationReadModel = {
  langCode: string;
  name: string;
  officialName?: string | null;
  localVariant?: string | null;
};
export type DistrictReadModel = {
  id: string;
  subdivisionCode: string;
  typeCode: string;
  oktmoPrefix?: string | null;
  fiasGuid?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  isActive?: boolean;
  sortOrder?: number;
  translations?: DistrictTranslationReadModel[];
};
export type DistrictListReadModel = {
  items: DistrictReadModel[];
  total: number;
};
export type CreateCountryRequest = {
  alpha2: string;
  alpha3: string;
  numeric: string;
};
export type UpdateCountryRequest = {
  alpha3?: string | null;
  numeric?: string | null;
};
export type CountryTranslationInput = {
  langCode: string;
  name: string;
  officialName?: string | null;
};
export type UpsertCountryTranslationsRequest = {
  translations: CountryTranslationInput[];
};
export type CountryCurrencyLinkReadModel = {
  currencyCode: string;
  isPrimary: boolean;
};
export type CountryCurrencyLinkInput = {
  currencyCode: string;
  isPrimary?: boolean;
};
export type SetCountryCurrenciesRequest = {
  currencies: CountryCurrencyLinkInput[];
};
export type CreateCurrencyRequest = {
  code: string;
  numeric: string;
  name: string;
  minorUnit?: number | null;
  isActive?: boolean;
  sortOrder?: number;
};
export type UpdateCurrencyRequest = {
  numeric?: string | null;
  name?: string | null;
  minorUnit?: number | null;
  isActive?: boolean | null;
  sortOrder?: number | null;
};
export type CurrencyTranslationInput = {
  langCode: string;
  name: string;
};
export type UpsertCurrencyTranslationsRequest = {
  translations: CurrencyTranslationInput[];
};
export type CreateLanguageRequest = {
  code: string;
  iso6391?: string | null;
  iso6392?: string | null;
  iso6393?: string | null;
  script?: string | null;
  nameEn: string;
  nameNative: string;
  direction?: string;
  isActive?: boolean;
  isDefault?: boolean;
  sortOrder?: number;
};
export type UpdateLanguageRequest = {
  iso6391?: string | null;
  iso6392?: string | null;
  iso6393?: string | null;
  script?: string | null;
  nameEn?: string | null;
  nameNative?: string | null;
  direction?: string | null;
  isActive?: boolean | null;
  isDefault?: boolean | null;
  sortOrder?: number | null;
};
export type CreateSubdivisionRequest = {
  code: string;
  countryCode: string;
  typeCode: string;
  parentCode?: string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  sortOrder?: number;
  isActive?: boolean;
};
export type UpdateSubdivisionRequest = {
  typeCode?: string | null;
  parentCode?: string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  sortOrder?: number | null;
  isActive?: boolean | null;
};
export type SubdivisionTranslationInput = {
  langCode: string;
  name: string;
  officialName?: string | null;
  localVariant?: string | null;
};
export type UpsertSubdivisionTranslationsRequest = {
  translations: SubdivisionTranslationInput[];
};
export type SubdivisionTypeTranslationReadModel = {
  langCode: string;
  name: string;
};
export type SubdivisionTypeReadModel = {
  code: string;
  sortOrder: number;
  translations?: SubdivisionTypeTranslationReadModel[];
};
export type SubdivisionTypeListReadModel = {
  items: SubdivisionTypeReadModel[];
  total: number;
};
export type CreateSubdivisionTypeRequest = {
  code: string;
  sortOrder?: number;
};
export type UpdateSubdivisionTypeRequest = {
  sortOrder?: number | null;
};
export type SubdivisionTypeTranslationInput = {
  langCode: string;
  name: string;
};
export type UpsertSubdivisionTypeTranslationsRequest = {
  translations: SubdivisionTypeTranslationInput[];
};
export type CreateDistrictRequest = {
  subdivisionCode: string;
  typeCode: string;
  oktmoPrefix?: string | null;
  fiasGuid?: string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  sortOrder?: number;
  isActive?: boolean;
};
export type UpdateDistrictRequest = {
  typeCode?: string | null;
  oktmoPrefix?: string | null;
  fiasGuid?: string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  sortOrder?: number | null;
  isActive?: boolean | null;
};
export type DistrictTranslationInput = {
  langCode: string;
  name: string;
  officialName?: string | null;
  localVariant?: string | null;
};
export type UpsertDistrictTranslationsRequest = {
  translations: DistrictTranslationInput[];
};
export type DistrictTypeTranslationReadModel = {
  langCode: string;
  name: string;
};
export type DistrictTypeReadModel = {
  code: string;
  sortOrder: number;
  translations?: DistrictTypeTranslationReadModel[];
};
export type DistrictTypeListReadModel = {
  items: DistrictTypeReadModel[];
  total: number;
};
export type CreateDistrictTypeRequest = {
  code: string;
  sortOrder?: number;
};
export type UpdateDistrictTypeRequest = {
  sortOrder?: number | null;
};
export type DistrictTypeTranslationInput = {
  langCode: string;
  name: string;
};
export type UpsertDistrictTypeTranslationsRequest = {
  translations: DistrictTypeTranslationInput[];
};
export type RegisterResponse = {
  identityId: string;
  message?: string;
};
export type RegisterRequest = {
  email: string;
  password: string;
  username?: string | null;
};
export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType?: string;
};
export type LoginRequest = {
  login: string;
  password: string;
};
export type TelegramTokenResponse = {
  accessToken: string;
  refreshToken: string;
  tokenType?: string;
  isNewUser: boolean;
};
export type RefreshTokenRequest = {
  refreshToken: string;
};
export type MessageResponse = {
  message: string;
};
export type InvitationInfoResponse = {
  email: string;
  roles: string[];
  expiresAt: string;
};
export type AcceptInvitationRequest = {
  password: string;
  firstName?: string;
  lastName?: string;
};
export type ProfileResponse = {
  id: string;
  profileEmail: string | null;
  firstName: string;
  lastName: string;
  username: string | null;
  photoUrl: string | null;
  phone: string | null;
};
export type UpdateProfileRequest = {
  firstName?: string | null;
  lastName?: string | null;
  phone?: string | null;
  profileEmail?: string | null;
};
export type ChangePasswordRequest = {
  currentPassword: string;
  newPassword: string;
};
export type SessionInfo = {
  id: string;
  ipAddress: string | null;
  userAgent: string | null;
  createdAt: string;
  expiresAt: string;
  isCurrent?: boolean;
};
export type AdminIdentityResponse = {
  identityId: string;
  email: string | null;
  authType: string;
  isActive: boolean;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
  roles: string[];
  createdAt: string;
};
export type AdminIdentityListResponse = {
  items: AdminIdentityResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type RoleInfoResponse = {
  id: string;
  name: string;
  description: string | null;
  isSystem: boolean;
};
export type AdminIdentityDetailResponse = {
  identityId: string;
  email: string | null;
  authType: string;
  isActive: boolean;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
  roles: RoleInfoResponse[];
  createdAt: string;
  deactivatedAt: string | null;
  deactivatedBy: string | null;
};
export type AdminDeactivateRequest = {
  reason: string;
};
export type RoleWithPermissions = {
  id: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  permissions: string[];
};
export type CreateRoleResponse = {
  roleId: string;
  message?: string;
};
export type CreateRoleRequest = {
  name: string;
  description?: string | null;
};
export type PermissionDetailResponse = {
  id: string;
  codename: string;
  resource: string;
  action: string;
  description: string | null;
};
export type RoleDetailResponse = {
  id: string;
  name: string;
  description: string | null;
  isSystem: boolean;
  permissions: PermissionDetailResponse[];
};
export type UpdateRoleRequest = {
  name?: string | null;
  description?: string | null;
};
export type SetRolePermissionsRequest = {
  permissionIds: string[];
};
export type PermissionInfoResponse = {
  id: string;
  codename: string;
  resource: string;
  action: string;
  description: string | null;
};
export type PermissionGroupResponse = {
  resource: string;
  permissions: PermissionInfoResponse[];
};
export type AssignRoleRequest = {
  roleId: string;
};
export type StaffListItemResponse = {
  identityId: string;
  email: string | null;
  firstName: string;
  lastName: string;
  position: string | null;
  department: string | null;
  roles: string[];
  isActive: boolean;
  createdAt: string;
};
export type StaffListResponse = {
  items: StaffListItemResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type InviteStaffResponse = {
  invitationId: string;
  inviteUrl: string;
};
export type InviteStaffRequest = {
  email: string;
  roleIds: string[];
};
export type InvitationListItemResponse = {
  id: string;
  email: string;
  status: string;
  invitedByEmail: string | null;
  roles: string[];
  createdAt: string;
  expiresAt: string;
};
export type InvitationListResponse = {
  items: InvitationListItemResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type StaffDetailResponse = {
  identityId: string;
  email: string | null;
  authType: string;
  isActive: boolean;
  firstName: string;
  lastName: string;
  position: string | null;
  department: string | null;
  roles: RoleInfoResponse[];
  createdAt: string;
  deactivatedAt: string | null;
  deactivatedBy: string | null;
  invitedBy: string;
};
export type CustomerListItemResponse = {
  identityId: string;
  email: string | null;
  firstName: string;
  lastName: string;
  phone: string | null;
  username?: string | null;
  authMethods?: string[];
  roles: string[];
  isActive: boolean;
  createdAt: string;
};
export type CustomerListResponse = {
  items: CustomerListItemResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type CustomerDetailResponse = {
  identityId: string;
  email: string | null;
  authType: string;
  isActive: boolean;
  firstName: string;
  lastName: string;
  phone: string | null;
  username?: string | null;
  authMethods?: string[];
  roles: RoleInfoResponse[];
  createdAt: string;
  deactivatedAt: string | null;
  deactivatedBy: string | null;
};
export type SupplierCreateResponse = {
  id: string;
};
export type SupplierCreateRequest = {
  name: string;
  type: string;
  /** ISO 3166-1 alpha-2 country code */
  countryCode: string;
  /** ISO 3166-2 subdivision code (optional) */
  subdivisionCode?: string | null;
};
export type SupplierResponse = {
  id: string;
  name: string;
  type: string;
  countryCode: string;
  subdivisionCode: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
};
export type SupplierListResponse = {
  items: SupplierResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type SupplierUpdateRequest = {
  name?: string | null;
  /** ISO 3166-1 alpha-2 country code */
  countryCode?: string | null;
  /** ISO 3166-2 subdivision code; send null to clear */
  subdivisionCode?: string | null;
};
export type StorefrontValueResponse = {
  id: string;
  code: string;
  slug: string;
  valueI18N: {
    [key: string]: string;
  };
  metaData: {
    [key: string]: any;
  };
  valueGroup?: string | null;
  sortOrder: number;
};
export type StorefrontFilterAttributeResponse = {
  attributeId: string;
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  /** Projected name from nameI18n when ?lang is specified */
  name?: string | null;
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  selectionMode: string;
  values: StorefrontValueResponse[];
  filterSettings?: {
    [key: string]: any;
  } | null;
  sortOrder: number;
};
export type StorefrontFilterListResponse = {
  categoryId: string;
  attributes: StorefrontFilterAttributeResponse[];
};
export type StorefrontCardAttributeResponse = {
  attributeId: string;
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  /** Projected name from nameI18n when ?lang is specified */
  name?: string | null;
  dataType: string;
  uiType: string;
  level: string;
  requirementLevel: string;
  sortOrder: number;
};
export type StorefrontCardGroupResponse = {
  groupId: string | null;
  groupCode: string | null;
  groupNameI18N: {
    [key: string]: string;
  };
  groupSortOrder: number;
  attributes: StorefrontCardAttributeResponse[];
};
export type StorefrontCardResponse = {
  categoryId: string;
  groups: StorefrontCardGroupResponse[];
};
export type StorefrontComparisonAttributeResponse = {
  attributeId: string;
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  /** Projected name from nameI18n when ?lang is specified */
  name?: string | null;
  dataType: string;
  uiType: string;
  sortOrder: number;
};
export type StorefrontComparisonResponse = {
  categoryId: string;
  attributes: StorefrontComparisonAttributeResponse[];
};
export type StorefrontFormAttributeResponse = {
  attributeId: string;
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  /** Projected name from nameI18n when ?lang is specified */
  name?: string | null;
  descriptionI18N: {
    [key: string]: string;
  };
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  level: string;
  requirementLevel: string;
  isFilterable: boolean;
  isVisibleOnCard: boolean;
  isComparable: boolean;
  validationRules?: {
    [key: string]: any;
  } | null;
  values: StorefrontValueResponse[];
  sortOrder: number;
};
export type StorefrontFormGroupResponse = {
  groupId: string | null;
  groupCode: string | null;
  groupNameI18N: {
    [key: string]: string;
  };
  groupSortOrder: number;
  attributes: StorefrontFormAttributeResponse[];
};
export type StorefrontFormResponse = {
  categoryId: string;
  groups: StorefrontFormGroupResponse[];
};
export type CategoryTreeResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  slug: string;
  fullSlug: string;
  level: number;
  sortOrder: number;
  children: CategoryTreeResponse[];
};
export type CategoryResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  slug: string;
  fullSlug: string;
  level: number;
  sortOrder: number;
  parentId?: string | null;
  version?: number;
};
export type PaginatedResponseCategoryResponse = {
  items: CategoryResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseCategoryResponseRead = {
  items: CategoryResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type BrandResponse = {
  id: string;
  name: string;
  slug: string;
  logoUrl?: string | null;
  version?: number;
};
export type PaginatedResponseBrandResponse = {
  items: BrandResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseBrandResponseRead = {
  items: BrandResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type StorefrontImageResponse = {
  url: string;
  /** Responsive variants for the image, e.g. [{size, width, height, url}, ...] */
  imageVariants?:
    | {
        [key: string]: any;
      }[]
    | null;
};
export type StorefrontMoneyResponse = {
  /** Amount in the smallest currency unit (e.g. kopecks) */
  amount: number;
  currency?: string;
  /** Original (strike-through) price before discount */
  compareAt?: number | null;
};
export type StorefrontBrandResponse = {
  id: string;
  name: string;
  slug: string;
  logoUrl?: string | null;
};
export type StorefrontSupplierResponse = {
  /** SupplierType enum value: 'cross_border' or 'local' */
  type: string;
};
export type StorefrontVariantOptionValueResponse = {
  valueId: string;
  valueCode: string;
  valueI18N?: {
    [key: string]: string;
  };
  value?: string | null;
  metaData?: {
    [key: string]: any;
  };
  sortOrder?: number;
};
export type StorefrontVariantOptionResponse = {
  attributeId: string;
  attributeCode: string;
  attributeNameI18N?: {
    [key: string]: string;
  };
  attributeName?: string | null;
  sortOrder?: number;
  values?: StorefrontVariantOptionValueResponse[];
};
export type StorefrontProductCardResponse = {
  id: string;
  slug: string;
  titleI18N: {
    [key: string]: string;
  };
  title?: string | null;
  image?: StorefrontImageResponse | null;
  images?: StorefrontImageResponse[];
  price?: StorefrontMoneyResponse | null;
  brand?: StorefrontBrandResponse | null;
  supplier?: StorefrontSupplierResponse | null;
  popularityScore?: number;
  publishedAt?: string | null;
  variantCount?: number;
  inStock?: boolean;
  variantOptions?: StorefrontVariantOptionResponse[];
};
export type FacetValueResponse = {
  valueId: string;
  code: string;
  slug: string;
  valueI18N?: {
    [key: string]: string | null;
  };
  metaData?: {
    [key: string]: any;
  };
  valueGroup?: string | null;
  sortOrder?: number;
  count?: number;
};
export type FacetGroupResponse = {
  attributeId: string;
  code: string;
  slug: string;
  nameI18N?: {
    [key: string]: string | null;
  };
  uiType?: string;
  selectionMode?: string;
  values?: FacetValueResponse[];
};
export type BrandFacetResponse = {
  brandId: string;
  name: string;
  slug: string;
  logoUrl?: string | null;
  count?: number;
};
export type PriceRangeResponse = {
  minPrice: number;
  maxPrice: number;
  currency?: string;
};
export type FacetResultResponse = {
  attributeFacets?: FacetGroupResponse[];
  brandFacets?: BrandFacetResponse[];
  priceRange?: PriceRangeResponse | null;
  totalProducts?: number;
};
export type StorefrontPlpResponse = {
  items?: StorefrontProductCardResponse[];
  hasNext?: boolean;
  nextCursor?: string | null;
  total?: number | null;
  facets?: FacetResultResponse | null;
};
export type StorefrontVariantAttributePairResponse = {
  attributeId: string;
  attributeValueId: string;
  attributeCode?: string | null;
  attributeNameI18N?: {
    [key: string]: string;
  };
  attributeName?: string | null;
  valueCode?: string | null;
  valueI18N?: {
    [key: string]: string;
  };
  value?: string | null;
  sortOrder?: number;
};
export type StorefrontSkuResponse = {
  id: string;
  skuCode: string;
  price?: StorefrontMoneyResponse | null;
  resolvedPrice?: StorefrontMoneyResponse | null;
  compareAtPrice?: StorefrontMoneyResponse | null;
  isActive?: boolean;
  variantAttributes?: StorefrontVariantAttributePairResponse[];
};
export type StorefrontVariantResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  name?: string | null;
  sortOrder?: number;
  skus?: StorefrontSkuResponse[];
};
export type StorefrontAttributeValueResponse = {
  attributeCode: string;
  attributeNameI18N: {
    [key: string]: string;
  };
  attributeName?: string | null;
  valueCode: string;
  valueI18N: {
    [key: string]: string;
  };
  value?: string | null;
  groupCode?: string | null;
  groupNameI18N?: {
    [key: string]: string;
  } | null;
  groupName?: string | null;
  sortOrder?: number;
};
export type BreadcrumbResponse = {
  labelI18N: {
    [key: string]: string;
  };
  slug: string;
  label?: string | null;
};
export type StorefrontProductDetailResponse = {
  id: string;
  slug: string;
  titleI18N: {
    [key: string]: string;
  };
  title?: string | null;
  descriptionI18N?: {
    [key: string]: string;
  };
  description?: string | null;
  brand?: StorefrontBrandResponse | null;
  supplier?: StorefrontSupplierResponse | null;
  price?: StorefrontMoneyResponse | null;
  popularityScore?: number;
  publishedAt?: string | null;
  variantCount?: number;
  inStock?: boolean;
  media?: StorefrontImageResponse[];
  variants?: StorefrontVariantResponse[];
  attributes?: StorefrontAttributeValueResponse[];
  variantOptions?: StorefrontVariantOptionResponse[];
  breadcrumbs?: BreadcrumbResponse[];
  tags?: string[];
  version?: number;
};
export type SearchSuggestionResponse = {
  /** Suggestion type: product, category, or brand */
  type: string;
  /** Display text */
  text: string;
  /** URL slug for navigation */
  slug: string;
  /** Additional data (logo_url, full_slug, etc.) */
  extra?: {
    [key: string]: any;
  } | null;
};
export type ForYouFeedResponse = {
  items: StorefrontProductCardResponse[];
  /** Opaque pagination token. Pass back in ``cursor`` query param. */
  nextCursor?: string | null;
  /** Ranking strategy version used to build this feed. */
  strategyVersion: string;
  /** True when the list was ranked using the caller's activity history.  False means the caller is anonymous or too new — the response is a cold-start fallback. */
  isPersonalized: boolean;
};
export type BrandCreateResponse = {
  id: string;
};
export type BrandCreateRequest = {
  name: string;
  slug: string;
  logoUrl?: string | null;
  logoStorageObjectId?: string | null;
};
export type BulkCreateBrandsResponse = {
  createdCount: number;
  skippedCount: number;
  ids: string[];
  skippedSlugs: string[];
};
export type BulkBrandItem = {
  name: string;
  slug: string;
  logoUrl?: string | null;
};
export type BulkCreateBrandsRequest = {
  items: BulkBrandItem[];
  /** If true, silently skip brands with existing slug/name instead of failing. */
  skipExisting?: boolean;
};
export type BrandUpdateRequest = {
  name?: string | null;
  slug?: string | null;
  logoUrl?: string | null;
  logoStorageObjectId?: string | null;
};
export type CategoryCreateResponse = {
  id: string;
  message: string;
};
export type CategoryCreateRequest = {
  nameI18N: {
    [key: string]: string;
  };
  slug: string;
  /** Parent category ID (optional) */
  parentId?: string | null;
  /** Display ordering among siblings */
  sortOrder?: number;
  /** Attribute template UUID. */
  templateId?: string | null;
};
export type BulkCategoryCreatedItemResponse = {
  id: string;
  slug: string;
  fullSlug: string;
  level: number;
  ref?: string | null;
};
export type BulkCreateCategoriesResponse = {
  createdCount: number;
  skippedCount: number;
  created: BulkCategoryCreatedItemResponse[];
  skippedSlugs: string[];
};
export type BulkCategoryItem = {
  nameI18N: {
    [key: string]: string;
  };
  slug: string;
  /** Existing parent category UUID */
  parentId?: string | null;
  /** Reference to another item's 'ref' in this batch (for nested trees) */
  parentRef?: string | null;
  /** Key so other items can reference this one as parent */
  ref?: string | null;
  sortOrder?: number;
  templateId?: string | null;
};
export type BulkCreateCategoriesRequest = {
  items: BulkCategoryItem[];
  /** If true, silently skip categories with conflicting slug instead of failing. */
  skipExisting?: boolean;
};
export type CategoryUpdateRequest = {
  nameI18N?: {
    [key: string]: string;
  } | null;
  slug?: string | null;
  sortOrder?: number | null;
  /** Attribute template UUID. */
  templateId?: string | null;
};
export type AttributeCreateResponse = {
  id: string;
};
export type AttributeCreateRequest = {
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  dataType: 'string' | 'integer' | 'float' | 'boolean';
  uiType: 'text_button' | 'color_swatch' | 'dropdown' | 'checkbox' | 'range_slider';
  isDictionary?: boolean;
  groupId?: string | null;
  level?: 'product' | 'variant';
  isFilterable?: boolean;
  isSearchable?: boolean;
  searchWeight?: number;
  isComparable?: boolean;
  isVisibleOnCard?: boolean;
  validationRules?: {
    [key: string]: any;
  } | null;
};
export type AttributeResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N: {
    [key: string]: string;
  };
  uiType: string;
  isDictionary: boolean;
  groupId: string | null;
  level: string;
  isFilterable: boolean;
  isSearchable: boolean;
  searchWeight: number;
  isComparable: boolean;
  isVisibleOnCard: boolean;
  validationRules?: {
    [key: string]: any;
  } | null;
};
export type AttributeResponseRead = {
  id: string;
  code: string;
  slug: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N: {
    [key: string]: string;
  };
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  groupId: string | null;
  level: string;
  isFilterable: boolean;
  isSearchable: boolean;
  searchWeight: number;
  isComparable: boolean;
  isVisibleOnCard: boolean;
  validationRules?: {
    [key: string]: any;
  } | null;
};
export type PaginatedResponseAttributeResponse = {
  items: AttributeResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseAttributeResponseRead = {
  items: AttributeResponseRead[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type BulkCreateAttributesResponse = {
  createdCount: number;
  skippedCount: number;
  ids: string[];
  skippedCodes: string[];
};
export type BulkCreateAttributesRequest = {
  items: AttributeCreateRequest[];
  /** If true, silently skip attributes with existing code/slug. */
  skipExisting?: boolean;
};
export type AttributeUpdateRequest = {
  nameI18N?: {
    [key: string]: string;
  } | null;
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  uiType?: ('text_button' | 'color_swatch' | 'dropdown' | 'checkbox' | 'range_slider') | null;
  groupId?: string | null;
  level?: ('product' | 'variant') | null;
  isFilterable?: boolean | null;
  isSearchable?: boolean | null;
  searchWeight?: number | null;
  isComparable?: boolean | null;
  isVisibleOnCard?: boolean | null;
  validationRules?: {
    [key: string]: any;
  } | null;
};
export type AttributeUsageTemplateItem = {
  id: string;
  code: string;
  nameI18N: {
    [key: string]: string;
  };
};
export type AttributeUsageCategoryItem = {
  id: string;
  fullSlug: string;
  nameI18N: {
    [key: string]: string;
  };
};
export type AttributeUsageResponse = {
  templateCount: number;
  templates: AttributeUsageTemplateItem[];
  categoryCount: number;
  categories: AttributeUsageCategoryItem[];
  productCount: number;
};
export type AttributeGroupCreateResponse = {
  id: string;
};
export type AttributeGroupCreateRequest = {
  code: string;
  nameI18N: {
    [key: string]: string;
  };
  sortOrder?: number;
};
export type AttributeGroupResponse = {
  id: string;
  code: string;
  nameI18N: {
    [key: string]: string;
  };
  sortOrder: number;
};
export type PaginatedResponseAttributeGroupResponse = {
  items: AttributeGroupResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseAttributeGroupResponseRead = {
  items: AttributeGroupResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type AttributeGroupUpdateRequest = {
  nameI18N?: {
    [key: string]: string;
  } | null;
  sortOrder?: number | null;
};
export type AttributeValueCreateResponse = {
  id: string;
};
export type AttributeValueCreateRequest = {
  code: string;
  slug: string;
  valueI18N: {
    [key: string]: string;
  };
  /** Search synonyms (max 50 entries, each max 100 chars) */
  searchAliases?: string[];
  metaData?: {
    [key: string]: any;
  };
  valueGroup?: string | null;
  /** Display ordering among values */
  sortOrder?: number;
};
export type AttributeValueResponse = {
  id: string;
  attributeId: string;
  valueI18N: {
    [key: string]: string;
  };
  searchAliases: string[];
  metaData: {
    [key: string]: any;
  };
  valueGroup?: string | null;
  sortOrder: number;
  isActive: boolean;
};
export type AttributeValueResponseRead = {
  id: string;
  attributeId: string;
  code: string;
  slug: string;
  valueI18N: {
    [key: string]: string;
  };
  searchAliases: string[];
  metaData: {
    [key: string]: any;
  };
  valueGroup?: string | null;
  sortOrder: number;
  isActive: boolean;
};
export type PaginatedResponseAttributeValueResponse = {
  items: AttributeValueResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseAttributeValueResponseRead = {
  items: AttributeValueResponseRead[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type BulkAddAttributeValuesResponse = {
  createdCount: number;
  ids: string[];
};
export type BulkAttributeValueItem = {
  code: string;
  slug: string;
  valueI18N: {
    [key: string]: string;
  };
  /** Search synonyms (max 50 entries, each max 100 chars) */
  searchAliases?: string[] | null;
  metaData?: {
    [key: string]: any;
  } | null;
  valueGroup?: string | null;
  sortOrder?: number;
};
export type BulkAddAttributeValuesRequest = {
  items: BulkAttributeValueItem[];
};
export type AttributeValueUpdateRequest = {
  valueI18N?: {
    [key: string]: string;
  } | null;
  searchAliases?: string[] | null;
  metaData?: {
    [key: string]: any;
  } | null;
  valueGroup?: string | null;
  sortOrder?: number | null;
};
export type AttributeValueActiveResponse = {
  id: string;
  isActive: boolean;
};
export type ReorderItemRequest = {
  valueId: string;
  sortOrder: number;
};
export type ReorderAttributeValuesRequest = {
  items: ReorderItemRequest[];
};
export type AttributeTemplateCreateResponse = {
  id: string;
  message?: string;
};
export type AttributeTemplateCreateRequest = {
  /** Unique machine-readable code. */
  code: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  sortOrder?: number;
};
export type AttributeTemplateResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N: {
    [key: string]: string;
  };
  sortOrder: number;
};
export type AttributeTemplateResponseRead = {
  id: string;
  code: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N: {
    [key: string]: string;
  };
  sortOrder: number;
};
export type PaginatedResponseAttributeTemplateResponse = {
  items: AttributeTemplateResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseAttributeTemplateResponseRead = {
  items: AttributeTemplateResponseRead[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type CloneAttributeTemplateResponse = {
  id: string;
  bindingsCopied: number;
  message?: string;
};
export type CloneAttributeTemplateRequest = {
  sourceTemplateId: string;
  /** Unique machine-readable code for the clone. */
  newCode: string;
  newNameI18N: {
    [key: string]: string;
  };
  newDescriptionI18N?: {
    [key: string]: string;
  } | null;
};
export type AttributeTemplateUpdateRequest = {
  nameI18N?: {
    [key: string]: string;
  } | null;
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  sortOrder?: number | null;
};
export type TemplateAttributeBindingEnrichedResponse = {
  id: string;
  affectedCategoriesCount: number;
  message?: string;
};
export type TemplateAttributeBindingRequest = {
  attributeId: string;
  sortOrder?: number;
  requirementLevel?: string;
  /** Opaque frontend config for filter UI (max 10 KB). Not interpreted by backend. */
  filterSettings?: {
    [key: string]: any;
  } | null;
};
export type TemplateAttributeBindingDetailResponse = {
  id: string;
  templateId: string;
  attributeId: string;
  sortOrder: number;
  requirementLevel: string;
  filterSettings?: {
    [key: string]: any;
  } | null;
  attributeCode?: string;
  attributeNameI18N?: {
    [key: string]: string;
  };
  attributeDataType?: string;
  attributeUiType?: string;
  attributeLevel?: string;
  attributeIsFilterable?: boolean;
};
export type PaginatedResponseTemplateAttributeBindingDetailResponse = {
  items: TemplateAttributeBindingDetailResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseTemplateAttributeBindingDetailResponseRead = {
  items: TemplateAttributeBindingDetailResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type TemplateAttributeBindingUpdateRequest = {
  sortOrder?: number | null;
  requirementLevel?: string | null;
  /** Opaque frontend config for filter UI (max 10 KB). Not interpreted by backend. */
  filterSettings?: {
    [key: string]: any;
  } | null;
};
export type BindingReorderItemSchema = {
  bindingId: string;
  sortOrder: number;
};
export type TemplateBindingReorderRequest = {
  items: BindingReorderItemSchema[];
};
export type ProductCreateResponse = {
  id: string;
  defaultVariantId: string;
  message: string;
};
export type ProductCreateRequest = {
  titleI18N: {
    [key: string]: string;
  };
  slug: string;
  brandId: string;
  primaryCategoryId: string;
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  supplierId?: string | null;
  sourceUrl?: string | null;
  countryOfOrigin?: string | null;
  tags?: string[];
};
export type ProductListItemResponse = {
  id: string;
  slug: string;
  titleI18N: {
    [key: string]: string;
  };
  status: string;
  brandId: string;
  primaryCategoryId: string;
  supplierId?: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
};
export type PaginatedResponseProductListItemResponse = {
  items: ProductListItemResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseProductListItemResponseRead = {
  items: ProductListItemResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type MissingAttributeItem = {
  attributeId: string;
  code: string;
  nameI18N: {
    [key: string]: string;
  };
};
export type ProductCompletenessResponse = {
  isComplete: boolean;
  totalRequired: number;
  filledRequired: number;
  totalRecommended: number;
  filledRecommended: number;
  missingRequired: MissingAttributeItem[];
  missingRecommended: MissingAttributeItem[];
};
export type MoneySchema = {
  amount: number;
  currency: string;
};
export type VariantAttributePairSchema = {
  attributeId: string;
  attributeValueId: string;
};
export type SkuResponse = {
  id: string;
  productId: string;
  variantId: string;
  skuCode: string;
  price?: MoneySchema | null;
  resolvedPrice?: MoneySchema | null;
  compareAtPrice?: MoneySchema | null;
  purchasePrice?: MoneySchema | null;
  sellingPrice?: MoneySchema | null;
  pricingStatus?: string;
  pricedAt?: string | null;
  pricedFailureReason?: string | null;
  isActive: boolean;
  version: number;
  createdAt: string;
  updatedAt: string;
  variantAttributes: VariantAttributePairSchema[];
};
export type ProductVariantResponse = {
  id: string;
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  sortOrder: number;
  defaultPrice?: MoneySchema | null;
  skus: SkuResponse[];
  version?: number;
};
export type ProductAttributeResponse = {
  id: string;
  productId: string;
  attributeId: string;
  attributeValueId: string;
  attributeCode?: string;
  attributeNameI18N?: {
    [key: string]: string;
  };
  attributeValueCode?: string;
  attributeValueNameI18N?: {
    [key: string]: string;
  };
};
export type ProductResponse = {
  id: string;
  slug: string;
  titleI18N: {
    [key: string]: string;
  };
  descriptionI18N: {
    [key: string]: string;
  };
  status: string;
  brandId: string;
  primaryCategoryId: string;
  supplierId?: string | null;
  sourceUrl?: string | null;
  countryOfOrigin?: string | null;
  tags: string[];
  version: number;
  createdAt: string;
  updatedAt: string;
  publishedAt?: string | null;
  minPrice?: number | null;
  maxPrice?: number | null;
  priceCurrency?: string | null;
  variants: ProductVariantResponse[];
  attributes: ProductAttributeResponse[];
};
export type ProductUpdateRequest = {
  titleI18N?: {
    [key: string]: string;
  } | null;
  slug?: string | null;
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  brandId?: string | null;
  primaryCategoryId?: string | null;
  supplierId?: string | null;
  countryOfOrigin?: string | null;
  tags?: string[] | null;
  version?: number | null;
};
export type BulkPurchasePriceItemError = {
  skuId: string;
  errorCode: string;
  message: string;
};
export type BulkPurchasePriceResponse = {
  updatedCount: number;
  unchangedCount: number;
  errors?: BulkPurchasePriceItemError[];
};
export type BulkPurchasePriceItemRequest = {
  skuId: string;
  purchasePrice: MoneySchema;
};
export type BulkPurchasePriceRequest = {
  items: BulkPurchasePriceItemRequest[];
};
export type ProductStatusChangeRequest = {
  status: 'draft' | 'enriching' | 'ready_for_review' | 'published' | 'archived';
};
export type FieldDiffSchema = {
  field: string;
  fromValue: any | null;
  toValue: any | null;
};
export type ValidationWarningSchema = {
  code: string;
  message: string;
  details: {
    [key: string]: any;
  };
};
export type ValidationErrorSchema = {
  code: string;
  message: string;
  field?: string | null;
};
export type ValidateUpdateResponse = {
  ok: boolean;
  diff: FieldDiffSchema[];
  warnings: ValidationWarningSchema[];
  validationErrors: ValidationErrorSchema[];
};
export type SkuPublishDiagnosticSchema = {
  skuId: string;
  skuCode: string;
  pricingStatus: string;
  hasManualPrice: boolean;
  hasSellingPrice: boolean;
  hasPurchasePrice: boolean;
  failureReason: string | null;
  nextStep: string;
};
export type ValidatePublishGateFailureSchema = {
  code: 'NO_ACTIVE_SKU' | 'ALL_SKUS_UNPRICED' | 'STATUS_NOT_TRANSITIONABLE';
  message: string;
};
export type ValidatePublishResponse = {
  ok: boolean;
  currentStatus: string;
  nextStatus: string;
  skuDiagnostics: SkuPublishDiagnosticSchema[];
  gateFailures: ValidatePublishGateFailureSchema[];
};
export type ProductVariantCreateResponse = {
  id: string;
  message: string;
};
export type ProductVariantCreateRequest = {
  nameI18N: {
    [key: string]: string;
  };
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  sortOrder?: number;
  defaultPrice?: MoneySchema | null;
};
export type PaginatedResponseProductVariantResponse = {
  items: ProductVariantResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseProductVariantResponseRead = {
  items: ProductVariantResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type ProductVariantUpdateResponse = {
  id: string;
  message: string;
  version?: number;
};
export type ProductVariantUpdateRequest = {
  nameI18N?: {
    [key: string]: string;
  } | null;
  descriptionI18N?: {
    [key: string]: string;
  } | null;
  sortOrder?: number | null;
  defaultPrice?: MoneySchema | null;
};
export type SkuCreateResponse = {
  id: string;
  message: string;
};
export type SkuCreateRequest = {
  skuCode: string;
  price?: MoneySchema | null;
  compareAtPrice?: MoneySchema | null;
  purchasePrice?: MoneySchema | null;
  isActive?: boolean;
  variantAttributes?: VariantAttributePairSchema[];
};
export type PaginatedResponseSkuResponse = {
  items: SkuResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseSkuResponseRead = {
  items: SkuResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type SkuMatrixGenerateResponse = {
  createdCount: number;
  skippedCount: number;
  skuIds: string[];
  message: string;
};
export type AttributeSelectionSchema = {
  attributeId: string;
  valueIds: string[];
};
export type SkuMatrixGenerateRequest = {
  attributeSelections: AttributeSelectionSchema[];
  price?: MoneySchema | null;
  compareAtPrice?: MoneySchema | null;
  isActive?: boolean;
};
export type SkuUpdateRequest = {
  skuCode?: string | null;
  price?: MoneySchema | null;
  compareAtPrice?: MoneySchema | null;
  purchasePrice?: MoneySchema | null;
  isActive?: boolean | null;
  variantAttributes?: VariantAttributePairSchema[] | null;
  version?: number | null;
};
export type ProductAttributeAssignResponse = {
  id: string;
  message: string;
};
export type ProductAttributeAssignRequest = {
  attributeId: string;
  attributeValueId: string;
};
export type PaginatedResponseProductAttributeResponse = {
  items: ProductAttributeResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseProductAttributeResponseRead = {
  items: ProductAttributeResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type BulkAssignProductAttributesResponse = {
  assignedCount: number;
  pavIds: string[];
  message: string;
};
export type BulkAssignProductAttributesRequest = {
  items: ProductAttributeAssignRequest[];
};
export type MediaAssetCreateResponse = {
  id: string;
  message: string;
};
export type MediaAssetCreateRequest = {
  storageObjectId?: string | null;
  variantId?: string | null;
  mediaType?: 'image' | 'video' | 'model_3d' | 'document';
  role?: 'main' | 'hover' | 'gallery' | 'hero_video' | 'size_guide' | 'packaging';
  sortOrder?: number;
  isExternal?: boolean;
  url?: string | null;
};
export type MediaAssetResponse = {
  id: string;
  productId: string;
  variantId?: string | null;
  mediaType: string;
  role: string;
  sortOrder: number;
  storageObjectId?: string | null;
  url?: string | null;
  isExternal: boolean;
  imageVariants?:
    | {
        [key: string]: any;
      }[]
    | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};
export type PaginatedResponseMediaAssetResponse = {
  items: MediaAssetResponse[];
  total: number;
  offset: number;
  limit: number;
};
export type PaginatedResponseMediaAssetResponseRead = {
  items: MediaAssetResponse[];
  total: number;
  offset: number;
  limit: number;
  /** True when more items exist beyond the current page. */
  hasNext: boolean;
};
export type MediaAssetUpdateResponse = {
  id: string;
  message: string;
};
export type MediaAssetUpdateRequest = {
  variantId?: string | null;
  role?: ('main' | 'hover' | 'gallery' | 'hero_video' | 'size_guide' | 'packaging') | null;
  sortOrder?: number | null;
};
export type ReorderMediaItemSchema = {
  mediaId: string;
  sortOrder: number;
};
export type MediaAssetReorderRequest = {
  items: ReorderMediaItemSchema[];
};
export type VariableResponse = {
  variableId: string;
  code: string;
  scope: string;
  dataType: string;
  unit: string;
  name: {
    [key: string]: string;
  };
  description: {
    [key: string]: string;
  };
  isRequired: boolean;
  defaultValue: string | null;
  isSystem: boolean;
  isFxRate: boolean;
  isUserEditableAtRuntime: boolean;
  maxAgeDays: number | null;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type VariableListResponse = {
  items: VariableResponse[];
  total: number;
};
export type VariableScope =
  | 'global'
  | 'supplier'
  | 'category'
  | 'range'
  | 'product_input'
  | 'sku_input';
export type CreateVariableResponse = {
  variableId: string;
  code: string;
  versionLock: number;
};
export type VariableDataType = 'decimal' | 'integer' | 'percent';
export type I18NText = {
  ru: string;
  en: string;
  [key: string]: any;
};
export type CreateVariableRequest = {
  /** Unique snake_case code. */
  code: string;
  /** Immutable after create. */
  scope: VariableScope;
  /** Immutable after create. */
  dataType: VariableDataType;
  /** Unit code (immutable). E.g. RUB, RUB/CNY, %. */
  unit: string;
  name: I18NText;
  description?: I18NText | null;
  isRequired?: boolean;
  defaultValue?: number | string | null;
  isSystem?: boolean;
  isFxRate?: boolean;
  maxAgeDays?: number | null;
};
export type UpdateVariableRequest = {
  expectedVersionLock?: number | null;
  name?: I18NText | null;
  description?: I18NText | null;
  isRequired?: boolean | null;
  defaultValue?: number | string | null;
  defaultValueProvided?: boolean;
  maxAgeDays?: number | null;
  maxAgeDaysProvided?: boolean;
  code?: string | null;
  scope?: VariableScope | null;
  dataType?: VariableDataType | null;
  unit?: string | null;
  isFxRate?: boolean | null;
};
export type PricingContextResponse = {
  contextId: string;
  code: string;
  name: {
    [key: string]: string;
  };
  isActive: boolean;
  isFrozen: boolean;
  freezeReason: string | null;
  roundingMode: string;
  roundingStep: string;
  marginFloorPct: string;
  evaluationTimeoutMs: number;
  simulationThreshold: number;
  approvalRequiredOnPublish: boolean;
  rangeBaseVariableCode: string | null;
  activeFormulaVersionId: string | null;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type ContextListResponse = {
  items: PricingContextResponse[];
  total: number;
};
export type CreateContextResponse = {
  contextId: string;
  code: string;
  versionLock: number;
};
export type RoundingMode = 'HALF_UP' | 'HALF_EVEN' | 'CEILING' | 'FLOOR';
export type CreateContextRequest = {
  code: string;
  name: I18NText;
  roundingMode?: RoundingMode;
  roundingStep?: number | string;
  marginFloorPct?: number | string;
  evaluationTimeoutMs?: number;
  simulationThreshold?: number;
  approvalRequiredOnPublish?: boolean;
  rangeBaseVariableCode?: string | null;
};
export type UpdateContextRequest = {
  expectedVersionLock?: number | null;
  code?: string | null;
  name?: I18NText | null;
  roundingMode?: RoundingMode | null;
  roundingStep?: number | string | null;
  marginFloorPct?: number | string | null;
  evaluationTimeoutMs?: number | null;
  simulationThreshold?: number | null;
  approvalRequiredOnPublish?: boolean | null;
  rangeBaseVariableCode?: string | null;
  rangeBaseVariableCodeProvided?: boolean;
};
export type MutateContextResponse = {
  contextId: string;
  versionLock: number;
};
export type FreezeContextRequest = {
  reason: string;
};
export type ContextGlobalValueItemResponse = {
  variableCode: string;
  value: string;
  variableName?: {
    [key: string]: string;
  };
  isRequired?: boolean;
};
export type ContextGlobalValuesResponse = {
  contextId: string;
  values: ContextGlobalValueItemResponse[];
  versionLock: number;
};
export type SetContextGlobalValueResponse = {
  contextId: string;
  variableCode: string;
  value: string;
  versionLock: number;
};
export type SetContextGlobalValueRequest = {
  /** New value for the global-scope variable on this context. */
  value: number | string;
  /** Current ``version_lock`` of the context (optimistic locking). */
  versionLock: number;
};
export type FormulaVersionResponse = {
  versionId: string;
  contextId: string;
  versionNumber: number;
  status: string;
  ast: {
    [key: string]: any;
  };
  publishedAt: string | null;
  publishedBy: string | null;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type FormulaVersionListResponse = {
  items: FormulaVersionResponse[];
  total: number;
};
export type FormulaStatus = 'draft' | 'published' | 'archived';
export type UpsertFormulaDraftResponse = {
  versionId: string;
  versionNumber: number;
  versionLock: number;
  created: boolean;
};
export type UpsertFormulaDraftRequest = {
  /** Formula AST (shape: {version: int, bindings: [{name, component_tag, expr}, ...]}). Last binding must have name='final_price' and component_tag='final_price'. */
  ast: {
    [key: string]: any;
  };
  /** Optimistic-lock value of the existing draft (if any). */
  expectedVersionLock?: number | null;
};
export type DiscardFormulaDraftResponse = {
  versionId: string;
};
export type PublishFormulaResponse = {
  versionId: string;
  versionNumber: number;
  previousVersionId: string | null;
};
export type RollbackFormulaResponse = {
  versionId: string;
  rolledBackFromVersionId: string | null;
};
export type PreviewPriceResponse = {
  /** Computed final price (Decimal). */
  finalPrice: string;
  /** Intermediate binding values, keyed by binding name. Includes ``final_price`` as the last entry. */
  components: {
    [key: string]: string;
  };
  formulaVersionId: string;
  formulaVersionNumber: number;
  contextId: string;
};
export type PreviewPriceRequest = {
  /** Product whose pricing profile supplies scope=product_input values. */
  productId: string;
  /** Category whose pricing settings supply scope=category values. Caller must provide this (no cross-module lookup in v1). */
  categoryId: string;
  /** Pricing context. Selects the published formula to use. */
  contextId: string;
  /** Optional supplier whose pricing settings supply scope=supplier values. When absent, supplier-scope variables fall back to their default values. */
  supplierId?: string | null;
};
export type FormulaBindingValue = {
  /** Machine identifier — referenced by ``ref:`` inside the formula AST. Unique within a formula version. */
  name: string;
  /** Authoring group/category tag (e.g. ``intermediate``, ``final_price``). May repeat across bindings — purely a UI hint. */
  componentTag: string;
  /** Human-readable label as authored on the formula. Falls back to ``null`` for legacy formulas that pre-date the field. */
  label?: string | null;
  /** Author-controlled visibility flag. ``False`` is a hint to the admin UI to collapse this binding under an expander. */
  isVisible?: boolean;
  /** Evaluator's computed value for this binding. ``null`` only if evaluation skipped this binding (should not happen in practice). */
  value?: string | null;
};
export type PreviewSkuPricingResponse = {
  /** Selling price the recompute pipeline would land. */
  finalPrice: string;
  /** Intermediate binding values keyed by binding name (admin-only). */
  components: {
    [key: string]: string;
  };
  /** Ordered list view of the formula's bindings paired with their evaluator-computed values. Admin-only — returned empty for non-admin callers, mirroring the ``components`` redaction. The list lets the UI render the formula step-by-step with the authored ``label`` instead of decoding snake_case keys from ``components``. */
  bindings?: FormulaBindingValue[];
  formulaVersionId: string;
  formulaVersionNumber: number;
  contextId: string;
};
export type PreviewSkuPricingRequest = {
  /** Product whose pricing profile supplies product-input values. ``null`` during the create-product flow before the product is persisted — variable resolution falls back to defaults (CAT-022). */
  productId?: string | null;
  /** Category for scope=category values. */
  categoryId: string;
  /** Pricing context — selects the published formula. */
  contextId: string;
  /** Hypothetical wholesale cost (``RUB`` or ``CNY``). */
  purchasePrice: MoneySchema;
  /** Optional supplier for scope=supplier overrides. */
  supplierId?: string | null;
};
export type ProductPricingProfileResponse = {
  profileId: string;
  productId: string;
  contextId: string | null;
  values: {
    [key: string]: string;
  };
  status: string;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type UpsertProductPricingProfileResponse = {
  profileId: string;
  productId: string;
  versionLock: number;
  status: string;
  created: boolean;
};
export type ProfileStatus = 'draft' | 'ready' | 'stale';
export type UpsertProductPricingProfileRequest = {
  /** Map of variable_code -> decimal value (e.g. {'purchase_price_cny': '199.50'}). */
  values?: {
    [key: string]: number | string;
  };
  /** Resolved pricing context ID (optional in this slice). */
  contextId?: string | null;
  /** Set to true if the caller is intentionally writing `context_id` (including null to clear it). False = leave existing value untouched. */
  contextIdProvided?: boolean;
  /** Desired profile status. */
  status?: ProfileStatus;
  /** Expected current `version_lock` for optimistic locking; required when updating an existing profile. Omit on create. */
  expectedVersionLock?: number | null;
};
export type RequiredVariableItem = {
  variableId: string;
  code: string;
  name: {
    [key: string]: string;
  };
  description?: {
    [key: string]: string;
  };
  dataType: VariableDataType;
  unit?: string | null;
  defaultValue?: string | null;
  isSystem?: boolean;
};
export type RequiredVariablesResponse = {
  productId: string;
  variables: RequiredVariableItem[];
};
export type SupplierPricingSettingsResponse = {
  id: string;
  supplierId: string;
  values: {
    [key: string]: string;
  };
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type UpsertSupplierPricingSettingsResponse = {
  settingsId: string;
  supplierId: string;
  versionLock: number;
  created: boolean;
};
export type UpsertSupplierPricingSettingsRequest = {
  /** Supplier-level variable values (e.g. supplier margin). */
  values?: {
    [key: string]: number | string;
  };
  /** Optional optimistic-locking guard; rejected with 409 if mismatched. */
  expectedVersionLock?: number | null;
};
export type SupplierTypeContextMappingResponse = {
  id: string;
  supplierType: string;
  contextId: string;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type SupplierTypeContextMappingListResponse = {
  items: SupplierTypeContextMappingResponse[];
};
export type UpsertSupplierTypeContextMappingResponse = {
  mappingId: string;
  supplierType: string;
  contextId: string;
  versionLock: number;
  created: boolean;
};
export type UpsertSupplierTypeContextMappingRequest = {
  /** Target pricing context id. */
  contextId: string;
};
export type RangeBucketSchema = {
  /** Stable UUID of the bucket (frontend may omit to get a new one). */
  id?: string;
  /** Inclusive lower bound (>= 0). */
  min: string;
  /** Exclusive upper bound. ``null`` is allowed only on the last bucket. */
  max?: string | null;
  /** Per-range variable overrides, snake_case codes. */
  values?: {
    [key: string]: string;
  };
};
export type CategoryPricingSettingsResponse = {
  id: string;
  categoryId: string;
  contextId: string;
  values: {
    [key: string]: string;
  };
  ranges: RangeBucketSchema[];
  explicitNoRanges: boolean;
  versionLock: number;
  createdAt: string;
  updatedAt: string;
  updatedBy: string | null;
};
export type UpsertCategoryPricingSettingsResponse = {
  settingsId: string;
  categoryId: string;
  contextId: string;
  versionLock: number;
  created: boolean;
};
export type RangeBucketSchema2 = {
  /** Stable UUID of the bucket (frontend may omit to get a new one). */
  id?: string;
  /** Inclusive lower bound (>= 0). */
  min: number | string;
  /** Exclusive upper bound. ``null`` is allowed only on the last bucket. */
  max?: number | string | null;
  /** Per-range variable overrides, snake_case codes. */
  values?: {
    [key: string]: number | string;
  };
};
export type UpsertCategoryPricingSettingsRequest = {
  /** Category-level variable values (e.g. default margin_pct). */
  values?: {
    [key: string]: number | string;
  };
  /** Ordered list of non-overlapping contiguous buckets. When ``explicit_no_ranges=true`` this MUST be empty. */
  ranges?: RangeBucketSchema2[];
  /** Set to ``true`` to explicitly declare that this category has no range buckets (disables any inherited ranges). Mutually exclusive with a non-empty ``ranges``. */
  explicitNoRanges?: boolean;
  /** Optional optimistic-locking guard; rejected with 409 if mismatched. */
  expectedVersionLock?: number | null;
};
export type RecomputeSkuResponse = {
  skuId: string;
  /** One of: priced, noop, missing_purchase_price, stale_fx, formula_error, sku_not_found, context_not_configured */
  status: string;
};
export type RecomputeFanoutResponse = {
  scope: string;
  scopeId: string;
  enqueued?: boolean;
};
export type TrendingProductEntry = {
  /** Product UUID */
  productId: string;
  /** Raw view-count score within the window */
  score: number;
};
export type TrendingProductsResponse = {
  /** Ranking window, e.g. "daily" or "weekly" */
  window: string;
  /** Category filter, if any */
  categoryId?: string | null;
  items?: TrendingProductEntry[];
};
export type SearchQueryEntry = {
  /** Normalised search query */
  query: string;
  /** Occurrence count within the window */
  count: number;
};
export type SearchAnalyticsResponse = {
  popular?: SearchQueryEntry[];
  zeroResults?: SearchQueryEntry[];
};
export type AddItemResponse = {
  cartId: string;
  itemId: string;
};
export type AddItemRequest = {
  skuId: string;
  quantity?: number;
};
export type UpdateQuantityRequest = {
  quantity: number;
};
export type MoneyResponse = {
  /** Amount in smallest currency unit (kopecks) */
  amount: number;
  currency?: string;
};
export type CartItemResponse = {
  id: string;
  skuId: string;
  productId: string;
  variantId: string;
  productName?: string | null;
  variantLabel?: string | null;
  imageUrl?: string | null;
  quantity: number;
  unitPrice?: MoneyResponse | null;
  lineTotal?: MoneyResponse | null;
  supplierType: string;
  addedAt?: string | null;
};
export type CartGroupResponse = {
  supplierType: string;
  items: CartItemResponse[];
  subtotal: MoneyResponse;
};
export type CartResponse = {
  id: string;
  status: string;
  itemCount: number;
  total: MoneyResponse;
  groups: CartGroupResponse[];
  createdAt?: string | null;
  updatedAt?: string | null;
};
export type CartSummaryResponse = {
  itemCount: number;
  total: MoneyResponse;
};
export type CheckoutInitiatedResponse = {
  attemptId: string;
  snapshotId: string;
  expiresAt: string;
};
export type InitiateCheckoutRequest = {
  pickupPointId: string;
  pickupCarrier: string;
  recipientId: string;
};
export type CheckoutConfirmedResponse = {
  orderId?: string | null;
};
export type ConfirmCheckoutRequest = {
  attemptId: string;
};
export type MergeCartRequest = {
  anonymousToken: string;
};
export type AnonymousTokenResponse = {
  token: string;
};
export type FavoriteListResponse = {
  id: string;
  name: string;
  isDefault: boolean;
  sortOrder: number;
  itemCount: number;
  createdAt: string;
  updatedAt: string;
};
export type FavoriteListsResponse = {
  items: FavoriteListResponse[];
};
export type CreateFavoriteListResponse = {
  id: string;
};
export type CreateFavoriteListRequest = {
  name: string;
};
export type RenameFavoriteListRequest = {
  name: string;
};
export type FavoriteTargetType = 'product' | 'brand';
export type FavoriteProductCardResponse = {
  id: string;
  slug: string;
  titleI18N: {
    [key: string]: string;
  };
  mainImageUrl?: string | null;
};
export type FavoriteBrandCardResponse = {
  id: string;
  slug: string;
  name: string;
  logoUrl?: string | null;
};
export type FavoriteItemResponse = {
  id: string;
  listId: string;
  targetType: FavoriteTargetType;
  targetId: string;
  addedAt: string;
  product?: FavoriteProductCardResponse | null;
  brand?: FavoriteBrandCardResponse | null;
};
export type FavoriteItemsPageResponse = {
  items: FavoriteItemResponse[];
  nextCursor?: string | null;
};
export type AddFavoriteItemResponse = {
  listId: string;
  itemId: string;
  created: boolean;
};
export type AddFavoriteItemRequest = {
  targetType: FavoriteTargetType;
  targetId: string;
  listId?: string | null;
};
export type MoveFavoriteItemRequest = {
  srcListId: string;
  dstListId: string;
  targetType: FavoriteTargetType;
  targetId: string;
};
export type CheckFavoritedResponse = {
  favorited: {
    [key: string]: string;
  };
};
export type CheckFavoritedRequest = {
  targetType: FavoriteTargetType;
  targetIds: string[];
};
export type UploadResponse = {
  storageObjectId: string;
  presignedUrl: string;
  expiresIn?: number;
};
export type UploadRequest = {
  contentType: string;
  filename?: string | null;
};
export type ReuploadResponse = {
  storageObjectId: string;
  presignedUrl: string;
  expiresIn?: number;
};
export type ReuploadRequest = {
  contentType: string;
  filename?: string | null;
};
export type ConfirmResponse = {
  storageObjectId: string;
  status?: string;
};
export type MediaVariant = {
  size: string;
  width: number;
  height: number;
  url: string;
};
export type MetadataResponse = {
  storageObjectId: string;
  status: string;
  url?: string | null;
  contentType?: string | null;
  sizeBytes?: number;
  variants?: MediaVariant[];
  createdAt?: string | null;
};
export type DeleteResponse = {
  deleted?: boolean;
};
export type ExternalImportResponse = {
  storageObjectId: string;
  url: string;
  variants?: MediaVariant[];
};
export type ExternalImportRequest = {
  url: string;
};
export type RemoveBackgroundResponse = {
  derivedStorageObjectId: string;
  status: 'processing' | 'completed' | 'failed';
  url?: string | null;
  alreadyExisted: boolean;
};
export type GeoPositionSchema = {
  latitude: number;
  longitude: number;
};
export type AddressSchema = {
  /** ISO 3166-1 alpha-2 */
  countryCode: string;
  city: string;
  region?: string | null;
  postalCode?: string | null;
  street?: string | null;
  house?: string | null;
  apartment?: string | null;
  /** ISO 3166-2 subdivision (optional) */
  subdivisionCode?: string | null;
  /** Provider-formatted single-line address, when available */
  rawAddress?: string | null;
};
export type DimensionsSchema = {
  lengthCm: number;
  widthCm: number;
  heightCm: number;
};
export type PickupPointSchema = {
  providerCode: 'cdek' | 'yandex_delivery';
  /** Opaque per-provider id; pass back to /rates/quote unchanged. */
  externalId: string;
  name: string;
  pickupPointType: 'pvz' | 'postamat' | 'post_office' | 'terminal';
  /** Marker coordinates — always present for map rendering */
  position: GeoPositionSchema;
  address: AddressSchema;
  /** Human-readable schedule string ('Пн-Пт 10:00-21:00'), provider-specific */
  workSchedule?: string | null;
  phone?: string | null;
  isCashAllowed: boolean;
  isCardAllowed: boolean;
  /** Provider-declared max parcel weight (grams) */
  weightLimitGrams?: number | null;
  /** Provider-declared max parcel dimensions */
  dimensionsLimit?: DimensionsSchema | null;
};
export type PickupPointsResponse = {
  points: PickupPointSchema[];
  /** provider_code → error message for providers that failed. */
  errors?: {
    [key: string]: string;
  };
};
export type PickupPointsRequest = {
  latitude?: number | null;
  longitude?: number | null;
  /** Bounding-box radius in km (default 10) */
  radiusKm?: number | null;
  city?: string | null;
  /** ISO 3166-1 alpha-2 */
  countryCode?: string | null;
  postalCode?: string | null;
  providerCode?: ('cdek' | 'yandex_delivery') | null;
  /** Filter by point capability (e.g. only PVZ for pickup_point) */
  deliveryType?: ('courier' | 'pickup_point' | 'post_office') | null;
};
export type CredentialFingerprintSchema = {
  /** First 8 hex chars of SHA-256(value). Stable per value. */
  fingerprint: string;
  /** Length of the original string value. */
  length: number;
};
export type ProviderAccountResponse = {
  id: string;
  providerCode: string;
  name: string;
  isActive: boolean;
  credentialFingerprints: {
    [key: string]: CredentialFingerprintSchema;
  };
  config: {
    [key: string]: any;
  };
  createdAt: string;
  updatedAt: string;
};
export type ProviderAccountListResponse = {
  items: ProviderAccountResponse[];
};
export type CreateProviderAccountRequest = {
  providerCode: string;
  name: string;
  credentials: {
    [key: string]: any;
  };
  config?: {
    [key: string]: any;
  };
  isActive?: boolean;
};
export type UpdateProviderAccountRequest = {
  name?: string | null;
  credentials?: {
    [key: string]: any;
  } | null;
  config?: {
    [key: string]: any;
  } | null;
  replaceConfig?: boolean;
};
export type SetProviderAccountActiveRequest = {
  isActive: boolean;
};
export type RefreshRegistryResponse = {
  registeredProviderCodes: string[];
  note?: string;
};
export type ShippingRateSchema = {
  providerCode: 'cdek' | 'yandex_delivery';
  serviceCode: string;
  serviceName: string;
  deliveryType: 'courier' | 'pickup_point' | 'post_office';
  totalCost: MoneySchema;
  baseCost: MoneySchema;
  insuranceCost?: MoneySchema | null;
  deliveryDaysMin?: number | null;
  deliveryDaysMax?: number | null;
};
export type DeliveryQuoteSchema = {
  id: string;
  rate: ShippingRateSchema;
  providerPayload: string;
  quotedAt: string;
  expiresAt?: string | null;
};
export type CalculateRatesResponse = {
  quotes: DeliveryQuoteSchema[];
  errors?: {
    [key: string]: string;
  };
};
export type WeightSchema = {
  /** Weight in grams */
  grams: number;
};
export type ParcelSchema = {
  weight: WeightSchema;
  dimensions?: DimensionsSchema | null;
  declaredValue?: MoneySchema | null;
  description?: string | null;
};
export type CalculateRatesRequest = {
  origin: AddressSchema;
  destination: AddressSchema;
  parcels: ParcelSchema[];
};
export type RateQuoteResponse = {
  quoteId: string;
  providerCode: 'cdek' | 'yandex_delivery';
  serviceCode: string;
  serviceName: string;
  deliveryType: 'courier' | 'pickup_point' | 'post_office';
  /** Customer-visible delivery cost (kopecks + currency) */
  deliveryAmount: MoneySchema;
  deliveryDaysMin?: number | null;
  deliveryDaysMax?: number | null;
  quotedAt: string;
  /** Quote becomes invalid after this moment (BRD: 30 minutes). Order placement re-checks and 409s on expiry. */
  expiresAt: string;
  /** Other ``service_code``s the provider returned for the same point — the frontend can offer them via re-quote. */
  fallbackAlternatives?: string[];
};
export type QuoteCartItemSchema = {
  skuId: string;
  quantity?: number;
};
export type RateQuoteRequest = {
  items: QuoteCartItemSchema[];
  providerCode: 'cdek' | 'yandex_delivery';
  /** ``PickupPointSchema.external_id`` from a previous /pickup-points response. Stale ids return 422. */
  pickupPointExternalId: string;
  /** Optional explicit tariff override (e.g. 'express'). Omitting it picks the cheapest tariff returned by the provider. */
  serviceCode?: string | null;
};
export type AdminShipmentSummarySchema = {
  id: string;
  /** Open provider identifier. Wider than ``ProviderCodeLiteral`` so legacy rows (e.g. dobropost) and rolled-back integrations still serialise. */
  providerCode: string;
  status: 'draft' | 'booking_pending' | 'booked' | 'cancel_pending' | 'cancelled' | 'failed';
  trackingNumber?: string | null;
  orderId?: string | null;
  deliveryType: 'courier' | 'pickup_point' | 'post_office';
  /** City of the recipient (extracted from destination payload). */
  destinationCity: string;
  quotedCost: MoneySchema;
  latestTrackingStatus?:
    | (
        | 'created'
        | 'accepted'
        | 'in_transit'
        | 'out_for_delivery'
        | 'ready_for_pickup'
        | 'delivered'
        | 'returned'
        | 'lost'
        | 'exception'
        | 'attempt_failed'
        | 'customs'
        | 'cancelled'
      )
    | null;
  createdAt: string;
  updatedAt: string;
  bookedAt?: string | null;
};
export type AdminShipmentListResponse = {
  items: AdminShipmentSummarySchema[];
  /** ``created_at`` of the last row when more rows are available; pass back as the ``cursor`` query param on the next request. ``None`` means no further pages. */
  nextCursor?: string | null;
};
export type ShipmentResponse = {
  id: string;
  orderId: string | null;
  providerCode: 'cdek' | 'yandex_delivery';
  serviceCode: string;
  deliveryType: 'courier' | 'pickup_point' | 'post_office';
  status: 'draft' | 'booking_pending' | 'booked' | 'cancel_pending' | 'cancelled' | 'failed';
  providerShipmentId?: string | null;
  trackingNumber?: string | null;
  quotedCost: MoneySchema;
  latestTrackingStatus?:
    | (
        | 'created'
        | 'accepted'
        | 'in_transit'
        | 'out_for_delivery'
        | 'ready_for_pickup'
        | 'delivered'
        | 'returned'
        | 'lost'
        | 'exception'
        | 'attempt_failed'
        | 'customs'
        | 'cancelled'
      )
    | null;
  createdAt: string;
  updatedAt: string;
  bookedAt?: string | null;
  cancelledAt?: string | null;
};
export type ContactInfoSchema = {
  firstName: string;
  lastName: string;
  /** E.164 phone (`+79991234567`); accepted in any format and normalised server-side. */
  phone: string;
  middleName?: string | null;
  email?: string | null;
  companyName?: string | null;
};
export type CashOnDeliverySchema = {
  amount: MoneySchema;
  paymentMethod?: ('cash' | 'card' | 'postpay') | null;
};
export type CreateShipmentRequest = {
  /** Result of /rates/quote within the last 30 minutes */
  quoteId: string;
  recipient: ContactInfoSchema;
  /** Optional caller correlation id */
  orderId?: string | null;
  cod?: CashOnDeliverySchema | null;
};
export type BookShipmentResponse = {
  shipmentId: string;
  providerShipmentId: string;
  trackingNumber?: string | null;
};
export type CancelShipmentResponse = {
  shipmentId: string;
};
export type TrackingEventSchema = {
  status:
    | 'created'
    | 'accepted'
    | 'in_transit'
    | 'out_for_delivery'
    | 'ready_for_pickup'
    | 'delivered'
    | 'returned'
    | 'lost'
    | 'exception'
    | 'attempt_failed'
    | 'customs'
    | 'cancelled';
  providerStatusCode: string;
  providerStatusName: string;
  timestamp: string;
  location?: string | null;
  description?: string | null;
};
export type TrackingResponse = {
  shipmentId: string;
  trackingNumber: string | null;
  latestStatus:
    | (
        | 'created'
        | 'accepted'
        | 'in_transit'
        | 'out_for_delivery'
        | 'ready_for_pickup'
        | 'delivered'
        | 'returned'
        | 'lost'
        | 'exception'
        | 'attempt_failed'
        | 'customs'
        | 'cancelled'
      )
    | null;
  events: TrackingEventSchema[];
};
export type IntakeWindowSchema = {
  /** ISO date (YYYY-MM-DD) */
  date: string;
  isWorkday?: boolean;
};
export type AvailableIntakeDaysResponse = {
  providerCode: 'cdek' | 'yandex_delivery';
  windows: IntakeWindowSchema[];
};
export type AvailableIntakeDaysRequest = {
  providerCode: 'cdek' | 'yandex_delivery';
  address: AddressSchema;
  /** Upper bound (YYYY-MM-DD) */
  until?: string | null;
};
export type CreateIntakeResponse = {
  shipmentId: string;
  providerIntakeId: string;
  status: 'accepted' | 'waiting' | 'delayed' | 'completed' | 'cancelled' | 'unknown';
};
export type CreateIntakeRequest = {
  /** Pickup date (YYYY-MM-DD) */
  intakeDate: string;
  /** Earliest time (HH:MM) */
  intakeTimeFrom: string;
  /** Latest time (HH:MM) */
  intakeTimeTo: string;
  comment?: string | null;
  lunchTimeFrom?: string | null;
  lunchTimeTo?: string | null;
  needCall?: boolean;
};
export type IntakeStatusResponse = {
  providerIntakeId: string;
  status: 'accepted' | 'waiting' | 'delayed' | 'completed' | 'cancelled' | 'unknown';
};
export type CancelIntakeResponse = {
  success: boolean;
};
export type DeliveryIntervalSchema = {
  /** HH:MM */
  startTime: string;
  /** HH:MM */
  endTime: string;
  /** YYYY-MM-DD if known */
  date?: string | null;
};
export type DeliveryIntervalsResponse = {
  providerCode: 'cdek' | 'yandex_delivery';
  intervals: DeliveryIntervalSchema[];
};
export type EstimatedDeliveryIntervalsRequest = {
  providerCode: 'cdek' | 'yandex_delivery';
  origin: AddressSchema;
  destination: AddressSchema;
  tariffCode: number;
};
export type ReturnResponse = {
  shipmentId: string;
  success: boolean;
  providerReturnId?: string | null;
  reason?: string | null;
};
export type ClientReturnRequest = {
  tariffCode: number;
  returnAddress: AddressSchema;
  sender: ContactInfoSchema;
  recipient: ContactInfoSchema;
};
export type RefusalRequestSchema = {
  /** Free-form audit note. Not forwarded to the provider. */
  reason?: string | null;
};
export type ReverseAvailabilityResponse = {
  providerCode: 'cdek' | 'yandex_delivery';
  isAvailable: boolean;
  reason?: string | null;
};
export type ReverseAvailabilityRequestSchema = {
  providerCode: 'cdek' | 'yandex_delivery';
  tariffCode: number;
  senderPhones: string[];
  recipientPhones: string[];
  fromLocation?: AddressSchema | null;
  toLocation?: AddressSchema | null;
  shipmentPoint?: string | null;
  deliveryPoint?: string | null;
  senderContragentType?: ('LEGAL_ENTITY' | 'INDIVIDUAL') | null;
  recipientContragentType?: ('LEGAL_ENTITY' | 'INDIVIDUAL') | null;
};
export type ActualDeliveryInfoSchema = {
  /** YYYY-MM-DD */
  deliveryDate: string;
  /** Local HH:MM */
  intervalStart: string;
  /** Local HH:MM */
  intervalEnd: string;
  /** e.g. "+03:00" */
  timezoneOffset?: string | null;
};
export type ActualDeliveryInfoResponse = {
  shipmentId: string;
  info?: ActualDeliveryInfoSchema | null;
};
export type EditTaskResponse = {
  shipmentId: string;
  taskId: string;
  initialStatus: 'pending' | 'execution' | 'success' | 'failure' | 'unknown';
};
export type EditPlaceSwapSchema = {
  oldBarcode: string;
  newBarcode: string;
  newParcel: ParcelSchema;
};
export type EditOrderRequest = {
  recipient?: ContactInfoSchema | null;
  destination?: AddressSchema | null;
  deliveryType?: ('courier' | 'pickup_point' | 'post_office') | null;
  places?: EditPlaceSwapSchema[];
};
export type EditPackageItemSchema = {
  itemBarcode: string;
  count: number;
};
export type EditPackageSchema = {
  barcode: string;
  weight: WeightSchema;
  dimensions: DimensionsSchema;
  items: EditPackageItemSchema[];
};
export type EditPackagesRequest = {
  packages: EditPackageSchema[];
};
export type EditItemMarkingSchema = {
  itemBarcode: string;
  article: string;
  markingCode?: string | null;
};
export type EditOrderItemsRequest = {
  items: EditItemMarkingSchema[];
};
export type EditItemRemovalSchema = {
  itemBarcode: string;
  /** 0 removes the item */
  remainingCount: number;
};
export type RemoveOrderItemsRequest = {
  removals: EditItemRemovalSchema[];
};
export type EditTaskStatusResponse = {
  providerCode: 'cdek' | 'yandex_delivery';
  taskId: string;
  status: 'pending' | 'execution' | 'success' | 'failure' | 'unknown';
};
export type CdekEditOrderResponse = {
  success: boolean;
  state?: string | null;
  requestUuid?: string | null;
  reason?: string | null;
};
export type CdekRawPayloadRequest = {
  /** CDEK API request body, forwarded to CDEK verbatim. */
  payload: {
    [key: string]: any;
  };
};
export type CdekJsonResponse = {
  /** CDEK response payload, as returned by CDEK. */
  data: any;
  /** CDEK error entries, if any. */
  errors?:
    | {
        [key: string]: any;
      }[]
    | null;
  /** CDEK warning entries, if any. */
  warnings?:
    | {
        [key: string]: any;
      }[]
    | null;
};
export type CdekWebhookSubscriptionRequest = {
  /** Client URL CDEK will POST events to. */
  url: string;
  /** CDEK webhook event type. */
  type: string;
};
export type CdekWebhookSyncResponse = {
  /** Subscriptions CDEK reported before the sync. */
  existing: {
    [key: string]: any;
  }[];
  /** Webhook types newly registered. */
  created: string[];
  /** Requested types that were already subscribed. */
  alreadyPresent: string[];
  /** Types skipped — registering them would exceed CDEK's 2-subscription cap. Free a slot first. */
  notCreated: string[];
};
export type CdekWebhookSyncRequest = {
  /** Client URL CDEK will POST events to. */
  url: string;
};
export type PaymentIntentSchema = {
  intentId: string;
  orderId: string;
  provider: string;
  amount: number;
  currency: string;
  status: string;
  providerReference: string | null;
  clientSecret: string | null;
  failureReason: string | null;
  createdAt: string;
  updatedAt: string;
};
export type SimulateCaptureRequest = {
  idempotencyKey: string;
};
export type CreateRecipientResponse = {
  recipientId: string;
};
export type CreateRecipientRequest = {
  fullNameRu: string;
  fullNameLat: string;
  phone: string;
  email: string;
  passportSerial: string;
  passportNumber: string;
  passportIssueDate: string;
  birthDate: string;
  inn: string;
};
export type RecipientSchema = {
  recipientId: string;
  fullNameRu: string;
  fullNameLat: string;
  phone: string;
  email: string;
  passportSerial: string;
  passportNumber: string;
  passportIssueDate: string;
  birthDate: string;
  inn: string;
  validationStatus: string;
  validationFailedReason: string | null;
  isArchived: boolean;
  createdAt: string;
  updatedAt: string;
  version?: number;
};
export type RecipientListResponse = {
  items: RecipientSchema[];
};
export type UpdateRecipientRequest = {
  fullNameRu?: string | null;
  fullNameLat?: string | null;
  phone?: string | null;
  email?: string | null;
  passportSerial?: string | null;
  passportNumber?: string | null;
  passportIssueDate?: string | null;
  birthDate?: string | null;
  inn?: string | null;
};
export type CreateOrderResponse = {
  orderId: string;
  paymentIntentId: string;
  clientSecret: string | null;
  totalAmount: number;
  currency: string;
};
export type CreateOrderRequest = {
  cartId: string;
  snapshotId: string;
  idempotencyKey: string;
  paymentProvider?: string;
};
export type OrderItemSchema = {
  itemId: string;
  skuId: string;
  productId: string;
  variantId: string;
  productName: string;
  variantLabel: string | null;
  supplierType: string;
  quantity: number;
  unitPriceAmount: number;
  currency: string;
  lineTotalAmount: number;
  crossBorderShipmentId: string | null;
  lastMileShipmentId: string | null;
};
export type CustomerOrderSchema = {
  orderId: string;
  orderNumber: string;
  status: string;
  rawStatus: string;
  totalAmount: number;
  currency: string;
  pickupCarrier: string;
  pickupPointId: string;
  incomingDeclaration: string | null;
  crossBorderTracking: string | null;
  lastMileTracking: string | null;
  createdAt: string;
  updatedAt: string;
  items: OrderItemSchema[];
};
export type CustomerOrderListResponse = {
  items: CustomerOrderSchema[];
  nextCursor: string | null;
};
export type TrackingStepSchema = {
  occurredAt: string;
  code: string;
  label: string;
  leg: string;
};
export type OrderTrackingResponse = {
  orderId: string;
  orderNumber: string;
  status: string;
  rawStatus: string;
  incomingDeclaration: string | null;
  crossBorderTrack: string | null;
  lastMileTrack: string | null;
  crossBorderStatusId: number | null;
  crossBorderStatusLabel: string | null;
  steps: TrackingStepSchema[];
};
export type CancellationReason =
  | 'customer_changed_mind'
  | 'customer_found_better_price'
  | 'customer_wrong_item'
  | 'customer_delivery_too_slow'
  | 'customer_duplicate_order'
  | 'merchant_out_of_stock'
  | 'merchant_price_error'
  | 'merchant_fraud_suspected'
  | 'merchant_region_not_served'
  | 'merchant_item_discontinued'
  | 'merchant_force_cancel'
  | 'system_payment_failed'
  | 'system_payment_timeout'
  | 'system_auth_expired'
  | 'system_hold_ttl_expired'
  | 'logistics_customs_rejected'
  | 'logistics_lost_in_transit'
  | 'logistics_undeliverable_address'
  | 'logistics_passport_invalid';
export type CancelOrderRequest = {
  reason?: CancellationReason;
  idempotencyKey: string;
};
export type ChangePickupPointRequest = {
  carrier: string;
  pointId: string;
};
export type CancellationReasonGroupSchema = {
  code: string;
  reasons: CancellationReason[];
};
export type CancellationReasonsMetaResponse = {
  categories: CancellationReasonGroupSchema[];
};
export type HoldReason =
  | 'passport_invalid'
  | 'customs_rejected'
  | 'stuck_in_cn'
  | 'manual_review'
  | 'booking_failed';
export type RecipientSnapshotSchema = {
  recipientId: string;
  fullNameRu: string;
  fullNameLat: string;
  phone: string;
  email: string;
  passportSerial: string;
  passportNumber: string;
  passportIssueDate: string;
  birthDate: string;
  inn: string;
};
export type AdminOrderSchema = {
  orderId: string;
  orderNumber: string;
  identityId: string;
  cartId: string;
  status: string;
  customerFacingStatus: string;
  totalAmount: number;
  currency: string;
  cnyRateAtCheckout: string | null;
  pickupCarrier: string;
  pickupPointId: string;
  paymentIntentId: string | null;
  incomingDeclaration: string | null;
  procuredByAdminId: string | null;
  procuredAt: string | null;
  crossBorderShipmentId: string | null;
  lastMileShipmentId: string | null;
  preHoldStatus: string | null;
  holdReason: HoldReason | null;
  holdStartedAt: string | null;
  holdUntil: string | null;
  cancellationReason: CancellationReason | null;
  createdAt: string;
  updatedAt: string;
  items: OrderItemSchema[];
  recipientSnapshot?: RecipientSnapshotSchema | null;
};
export type AdminOrderListResponse = {
  items: AdminOrderSchema[];
  nextCursor: string | null;
};
export type OrderStateHistoryEntrySchema = {
  id: string;
  fromStatus: string | null;
  toStatus: string;
  eventType: string;
  eventId: string;
  actorType: string;
  actorId: string;
  metadata: {
    [key: string]: any;
  } | null;
  occurredAt: string;
};
export type ProcureOrderRequest = {
  incomingDeclaration: string;
};
export type HoldOrderRequest = {
  reason: HoldReason;
};
export const {
  useListCountriesApiV1GeoCountriesGetQuery,
  useLazyListCountriesApiV1GeoCountriesGetQuery,
  useListCurrenciesApiV1GeoCurrenciesGetQuery,
  useLazyListCurrenciesApiV1GeoCurrenciesGetQuery,
  useListLanguagesApiV1GeoLanguagesGetQuery,
  useLazyListLanguagesApiV1GeoLanguagesGetQuery,
  useGetCountryApiV1GeoCountriesAlpha2GetQuery,
  useLazyGetCountryApiV1GeoCountriesAlpha2GetQuery,
  useGetCurrencyApiV1GeoCurrenciesCodeGetQuery,
  useLazyGetCurrencyApiV1GeoCurrenciesCodeGetQuery,
  useGetLanguageApiV1GeoLanguagesCodeGetQuery,
  useLazyGetLanguageApiV1GeoLanguagesCodeGetQuery,
  useGetSubdivisionApiV1GeoSubdivisionsCodeGetQuery,
  useLazyGetSubdivisionApiV1GeoSubdivisionsCodeGetQuery,
  useListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetQuery,
  useLazyListCountryCurrenciesApiV1GeoCountriesCountryCodeCurrenciesGetQuery,
  useListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetQuery,
  useLazyListSubdivisionsApiV1GeoCountriesCountryCodeSubdivisionsGetQuery,
  useGetDistrictApiV1GeoDistrictsDistrictIdGetQuery,
  useLazyGetDistrictApiV1GeoDistrictsDistrictIdGetQuery,
  useListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetQuery,
  useLazyListDistrictsApiV1GeoSubdivisionsSubdivisionCodeDistrictsGetQuery,
  useCreateCountryApiV1AdminGeoCountriesPostMutation,
  useUpdateCountryApiV1AdminGeoCountriesAlpha2PatchMutation,
  useDeleteCountryApiV1AdminGeoCountriesAlpha2DeleteMutation,
  useUpsertCountryTranslationsApiV1AdminGeoCountriesAlpha2TranslationsPutMutation,
  useSetCountryCurrenciesApiV1AdminGeoCountriesAlpha2CurrenciesPutMutation,
  useCreateCurrencyApiV1AdminGeoCurrenciesPostMutation,
  useUpdateCurrencyApiV1AdminGeoCurrenciesCodePatchMutation,
  useDeleteCurrencyApiV1AdminGeoCurrenciesCodeDeleteMutation,
  useUpsertCurrencyTranslationsApiV1AdminGeoCurrenciesCodeTranslationsPutMutation,
  useCreateLanguageApiV1AdminGeoLanguagesPostMutation,
  useUpdateLanguageApiV1AdminGeoLanguagesCodePatchMutation,
  useDeleteLanguageApiV1AdminGeoLanguagesCodeDeleteMutation,
  useCreateSubdivisionApiV1AdminGeoSubdivisionsPostMutation,
  useUpdateSubdivisionApiV1AdminGeoSubdivisionsCodePatchMutation,
  useDeleteSubdivisionApiV1AdminGeoSubdivisionsCodeDeleteMutation,
  useUpsertSubdivisionTranslationsApiV1AdminGeoSubdivisionsCodeTranslationsPutMutation,
  useListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetQuery,
  useLazyListSubdivisionTypesApiV1AdminGeoSubdivisionTypesGetQuery,
  useCreateSubdivisionTypeApiV1AdminGeoSubdivisionTypesPostMutation,
  useUpdateSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodePatchMutation,
  useDeleteSubdivisionTypeApiV1AdminGeoSubdivisionTypesCodeDeleteMutation,
  useUpsertSubdivisionTypeTranslationsApiV1AdminGeoSubdivisionTypesCodeTranslationsPutMutation,
  useCreateDistrictApiV1AdminGeoDistrictsPostMutation,
  useUpdateDistrictApiV1AdminGeoDistrictsDistrictIdPatchMutation,
  useDeleteDistrictApiV1AdminGeoDistrictsDistrictIdDeleteMutation,
  useUpsertDistrictTranslationsApiV1AdminGeoDistrictsDistrictIdTranslationsPutMutation,
  useListDistrictTypesApiV1AdminGeoDistrictTypesGetQuery,
  useLazyListDistrictTypesApiV1AdminGeoDistrictTypesGetQuery,
  useCreateDistrictTypeApiV1AdminGeoDistrictTypesPostMutation,
  useUpdateDistrictTypeApiV1AdminGeoDistrictTypesCodePatchMutation,
  useDeleteDistrictTypeApiV1AdminGeoDistrictTypesCodeDeleteMutation,
  useUpsertDistrictTypeTranslationsApiV1AdminGeoDistrictTypesCodeTranslationsPutMutation,
  useRegisterApiV1AuthRegisterPostMutation,
  useLoginApiV1AuthLoginPostMutation,
  useLoginTelegramApiV1AuthTelegramPostMutation,
  useRefreshTokenApiV1AuthRefreshPostMutation,
  useLogoutApiV1AuthLogoutPostMutation,
  useLogoutAllApiV1AuthLogoutAllPostMutation,
  useValidateInvitationApiV1InvitationsTokenValidateGetQuery,
  useLazyValidateInvitationApiV1InvitationsTokenValidateGetQuery,
  useAcceptInvitationApiV1InvitationsTokenAcceptPostMutation,
  useGetMyProfileApiV1ProfileMeGetQuery,
  useLazyGetMyProfileApiV1ProfileMeGetQuery,
  useDeleteMyAccountApiV1ProfileMeDeleteMutation,
  useUpdateProfileApiV1ProfileMePatchMutation,
  useChangePasswordApiV1ProfilePasswordPutMutation,
  useGetMySessionsApiV1ProfileSessionsGetQuery,
  useLazyGetMySessionsApiV1ProfileSessionsGetQuery,
  useListIdentitiesApiV1AdminIdentitiesGetQuery,
  useLazyListIdentitiesApiV1AdminIdentitiesGetQuery,
  useGetIdentityDetailApiV1AdminIdentitiesIdentityIdGetQuery,
  useLazyGetIdentityDetailApiV1AdminIdentitiesIdentityIdGetQuery,
  useAdminDeactivateIdentityApiV1AdminIdentitiesIdentityIdDeactivatePostMutation,
  useAdminReactivateIdentityApiV1AdminIdentitiesIdentityIdReactivatePostMutation,
  useListRolesApiV1AdminRolesGetQuery,
  useLazyListRolesApiV1AdminRolesGetQuery,
  useCreateRoleApiV1AdminRolesPostMutation,
  useGetRoleDetailApiV1AdminRolesRoleIdGetQuery,
  useLazyGetRoleDetailApiV1AdminRolesRoleIdGetQuery,
  useUpdateRoleApiV1AdminRolesRoleIdPatchMutation,
  useDeleteRoleApiV1AdminRolesRoleIdDeleteMutation,
  useSetRolePermissionsApiV1AdminRolesRoleIdPermissionsPutMutation,
  useListPermissionsApiV1AdminPermissionsGetQuery,
  useLazyListPermissionsApiV1AdminPermissionsGetQuery,
  useAssignRoleApiV1AdminIdentitiesIdentityIdRolesPostMutation,
  useRevokeRoleApiV1AdminIdentitiesIdentityIdRolesRoleIdDeleteMutation,
  useListStaffApiV1AdminStaffGetQuery,
  useLazyListStaffApiV1AdminStaffGetQuery,
  useInviteStaffApiV1AdminStaffInvitationsPostMutation,
  useListInvitationsApiV1AdminStaffInvitationsGetQuery,
  useLazyListInvitationsApiV1AdminStaffInvitationsGetQuery,
  useRevokeInvitationApiV1AdminStaffInvitationsInvitationIdDeleteMutation,
  useGetStaffDetailApiV1AdminStaffIdentityIdGetQuery,
  useLazyGetStaffDetailApiV1AdminStaffIdentityIdGetQuery,
  useDeactivateStaffApiV1AdminStaffIdentityIdDeactivatePostMutation,
  useReactivateStaffApiV1AdminStaffIdentityIdReactivatePostMutation,
  useListCustomersApiV1AdminCustomersGetQuery,
  useLazyListCustomersApiV1AdminCustomersGetQuery,
  useGetCustomerDetailApiV1AdminCustomersIdentityIdGetQuery,
  useLazyGetCustomerDetailApiV1AdminCustomersIdentityIdGetQuery,
  useDeactivateCustomerApiV1AdminCustomersIdentityIdDeactivatePostMutation,
  useReactivateCustomerApiV1AdminCustomersIdentityIdReactivatePostMutation,
  useCreateSupplierApiV1AdminSuppliersPostMutation,
  useListSuppliersApiV1AdminSuppliersGetQuery,
  useLazyListSuppliersApiV1AdminSuppliersGetQuery,
  useGetSupplierApiV1AdminSuppliersSupplierIdGetQuery,
  useLazyGetSupplierApiV1AdminSuppliersSupplierIdGetQuery,
  useUpdateSupplierApiV1AdminSuppliersSupplierIdPutMutation,
  useDeactivateSupplierApiV1AdminSuppliersSupplierIdDeactivatePatchMutation,
  useActivateSupplierApiV1AdminSuppliersSupplierIdActivatePatchMutation,
  useGetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetQuery,
  useLazyGetFilterableAttributesApiV1StorefrontCategoriesCategoryIdFiltersGetQuery,
  useGetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetQuery,
  useLazyGetCardAttributesApiV1StorefrontCategoriesCategoryIdCardAttributesGetQuery,
  useGetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetQuery,
  useLazyGetComparisonAttributesApiV1StorefrontCategoriesCategoryIdComparisonAttributesGetQuery,
  useGetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetQuery,
  useLazyGetFormAttributesApiV1StorefrontCategoriesCategoryIdFormAttributesGetQuery,
  useStorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetQuery,
  useLazyStorefrontCategoryTreeApiV1StorefrontCategoriesTreeGetQuery,
  useStorefrontListCategoriesApiV1StorefrontCategoriesGetQuery,
  useLazyStorefrontListCategoriesApiV1StorefrontCategoriesGetQuery,
  useStorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetQuery,
  useLazyStorefrontGetCategoryApiV1StorefrontCategoriesCategoryIdGetQuery,
  useStorefrontListBrandsApiV1StorefrontBrandsGetQuery,
  useLazyStorefrontListBrandsApiV1StorefrontBrandsGetQuery,
  useStorefrontGetBrandApiV1StorefrontBrandsBrandIdGetQuery,
  useLazyStorefrontGetBrandApiV1StorefrontBrandsBrandIdGetQuery,
  useListStorefrontProductsApiV1StorefrontProductsGetQuery,
  useLazyListStorefrontProductsApiV1StorefrontProductsGetQuery,
  useGetStorefrontProductApiV1StorefrontProductsSlugGetQuery,
  useLazyGetStorefrontProductApiV1StorefrontProductsSlugGetQuery,
  useGetSimilarProductsApiV1StorefrontProductsSlugSimilarGetQuery,
  useLazyGetSimilarProductsApiV1StorefrontProductsSlugSimilarGetQuery,
  useGetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetQuery,
  useLazyGetAlsoViewedProductsApiV1StorefrontProductsSlugAlsoViewedGetQuery,
  useSearchProductsApiV1StorefrontSearchGetQuery,
  useLazySearchProductsApiV1StorefrontSearchGetQuery,
  useSearchSuggestApiV1StorefrontSearchSuggestGetQuery,
  useLazySearchSuggestApiV1StorefrontSearchSuggestGetQuery,
  useListTrendingProductsApiV1StorefrontTrendingGetQuery,
  useLazyListTrendingProductsApiV1StorefrontTrendingGetQuery,
  useGetForYouFeedApiV1StorefrontForYouGetQuery,
  useLazyGetForYouFeedApiV1StorefrontForYouGetQuery,
  useCreateBrandApiV1AdminCatalogBrandsPostMutation,
  useListBrandsApiV1AdminCatalogBrandsGetQuery,
  useLazyListBrandsApiV1AdminCatalogBrandsGetQuery,
  useBulkCreateBrandsApiV1AdminCatalogBrandsBulkPostMutation,
  useGetBrandApiV1AdminCatalogBrandsBrandIdGetQuery,
  useLazyGetBrandApiV1AdminCatalogBrandsBrandIdGetQuery,
  useUpdateBrandApiV1AdminCatalogBrandsBrandIdPatchMutation,
  useDeleteBrandApiV1AdminCatalogBrandsBrandIdDeleteMutation,
  useCreateCategoryApiV1AdminCatalogCategoriesPostMutation,
  useListCategoriesApiV1AdminCatalogCategoriesGetQuery,
  useLazyListCategoriesApiV1AdminCatalogCategoriesGetQuery,
  useBulkCreateCategoriesApiV1AdminCatalogCategoriesBulkPostMutation,
  useGetCategoryTreeApiV1AdminCatalogCategoriesTreeGetQuery,
  useLazyGetCategoryTreeApiV1AdminCatalogCategoriesTreeGetQuery,
  useGetCategoryApiV1AdminCatalogCategoriesCategoryIdGetQuery,
  useLazyGetCategoryApiV1AdminCatalogCategoriesCategoryIdGetQuery,
  useUpdateCategoryApiV1AdminCatalogCategoriesCategoryIdPatchMutation,
  useDeleteCategoryApiV1AdminCatalogCategoriesCategoryIdDeleteMutation,
  useCreateAttributeApiV1AdminCatalogAttributesPostMutation,
  useListAttributesApiV1AdminCatalogAttributesGetQuery,
  useLazyListAttributesApiV1AdminCatalogAttributesGetQuery,
  useBulkCreateAttributesApiV1AdminCatalogAttributesBulkPostMutation,
  useGetAttributeApiV1AdminCatalogAttributesAttributeIdGetQuery,
  useLazyGetAttributeApiV1AdminCatalogAttributesAttributeIdGetQuery,
  useUpdateAttributeApiV1AdminCatalogAttributesAttributeIdPatchMutation,
  useDeleteAttributeApiV1AdminCatalogAttributesAttributeIdDeleteMutation,
  useGetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetQuery,
  useLazyGetAttributeUsageApiV1AdminCatalogAttributesAttributeIdUsageGetQuery,
  useCreateAttributeGroupApiV1AdminCatalogAttributeGroupsPostMutation,
  useListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetQuery,
  useLazyListAttributeGroupsApiV1AdminCatalogAttributeGroupsGetQuery,
  useGetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetQuery,
  useLazyGetAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdGetQuery,
  useUpdateAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdPatchMutation,
  useDeleteAttributeGroupApiV1AdminCatalogAttributeGroupsGroupIdDeleteMutation,
  useAddAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesPostMutation,
  useListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetQuery,
  useLazyListAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesGetQuery,
  useBulkAddAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesBulkPostMutation,
  useGetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetQuery,
  useLazyGetAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdGetQuery,
  useUpdateAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdPatchMutation,
  useDeleteAttributeValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeleteMutation,
  useDeactivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdDeactivatePatchMutation,
  useActivateValueApiV1AdminCatalogAttributesAttributeIdValuesValueIdActivatePatchMutation,
  useReorderAttributeValuesApiV1AdminCatalogAttributesAttributeIdValuesReorderPostMutation,
  useCreateTemplateApiV1AdminCatalogAttributeTemplatesPostMutation,
  useListTemplatesApiV1AdminCatalogAttributeTemplatesGetQuery,
  useLazyListTemplatesApiV1AdminCatalogAttributeTemplatesGetQuery,
  useCloneTemplateApiV1AdminCatalogAttributeTemplatesClonePostMutation,
  useGetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetQuery,
  useLazyGetTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdGetQuery,
  useUpdateTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdPatchMutation,
  useDeleteTemplateApiV1AdminCatalogAttributeTemplatesTemplateIdDeleteMutation,
  useBindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesPostMutation,
  useListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetQuery,
  useLazyListBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesGetQuery,
  useUpdateBindingApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdPatchMutation,
  useUnbindAttributeApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesBindingIdDeleteMutation,
  useReorderBindingsApiV1AdminCatalogAttributeTemplatesTemplateIdAttributesReorderPostMutation,
  useCreateProductApiV1AdminCatalogProductsPostMutation,
  useListProductsApiV1AdminCatalogProductsGetQuery,
  useLazyListProductsApiV1AdminCatalogProductsGetQuery,
  useGetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetQuery,
  useLazyGetProductCompletenessApiV1AdminCatalogProductsProductIdCompletenessGetQuery,
  useGetProductApiV1AdminCatalogProductsProductIdGetQuery,
  useLazyGetProductApiV1AdminCatalogProductsProductIdGetQuery,
  useUpdateProductApiV1AdminCatalogProductsProductIdPatchMutation,
  useDeleteProductApiV1AdminCatalogProductsProductIdDeleteMutation,
  useStreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetQuery,
  useLazyStreamSkuPricingEventsApiV1AdminCatalogProductsProductIdSkusPricingEventsGetQuery,
  useBulkSetPurchasePriceApiV1AdminCatalogProductsProductIdSkusBulkPurchasePricePostMutation,
  useChangeProductStatusApiV1AdminCatalogProductsProductIdStatusPatchMutation,
  useValidateProductUpdateApiV1AdminCatalogProductsProductIdValidateUpdatePostMutation,
  useValidateProductPublishApiV1AdminCatalogProductsProductIdValidatePublishPostMutation,
  useAddVariantApiV1AdminCatalogProductsProductIdVariantsPostMutation,
  useListVariantsApiV1AdminCatalogProductsProductIdVariantsGetQuery,
  useLazyListVariantsApiV1AdminCatalogProductsProductIdVariantsGetQuery,
  useUpdateVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdPatchMutation,
  useDeleteVariantApiV1AdminCatalogProductsProductIdVariantsVariantIdDeleteMutation,
  useAddSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusPostMutation,
  useListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetQuery,
  useLazyListSkusApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGetQuery,
  useGenerateSkuMatrixApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusGeneratePostMutation,
  useUpdateSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdPatchMutation,
  useDeleteSkuApiV1AdminCatalogProductsProductIdVariantsVariantIdSkusSkuIdDeleteMutation,
  useAssignProductAttributeApiV1AdminCatalogProductsProductIdAttributesPostMutation,
  useListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetQuery,
  useLazyListProductAttributesApiV1AdminCatalogProductsProductIdAttributesGetQuery,
  useBulkAssignProductAttributesApiV1AdminCatalogProductsProductIdAttributesBulkPostMutation,
  useDeleteProductAttributeApiV1AdminCatalogProductsProductIdAttributesAttributeIdDeleteMutation,
  useAddProductMediaApiV1AdminCatalogProductsProductIdMediaPostMutation,
  useListProductMediaApiV1AdminCatalogProductsProductIdMediaGetQuery,
  useLazyListProductMediaApiV1AdminCatalogProductsProductIdMediaGetQuery,
  useUpdateProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdPatchMutation,
  useDeleteProductMediaApiV1AdminCatalogProductsProductIdMediaMediaIdDeleteMutation,
  useReorderProductMediaApiV1AdminCatalogProductsProductIdMediaReorderPostMutation,
  useListVariablesApiV1AdminPricingVariablesGetQuery,
  useLazyListVariablesApiV1AdminPricingVariablesGetQuery,
  useCreateVariableApiV1AdminPricingVariablesPostMutation,
  useGetVariableApiV1AdminPricingVariablesVariableIdGetQuery,
  useLazyGetVariableApiV1AdminPricingVariablesVariableIdGetQuery,
  useUpdateVariableApiV1AdminPricingVariablesVariableIdPatchMutation,
  useDeleteVariableApiV1AdminPricingVariablesVariableIdDeleteMutation,
  useListContextsApiV1AdminPricingContextsGetQuery,
  useLazyListContextsApiV1AdminPricingContextsGetQuery,
  useCreateContextApiV1AdminPricingContextsPostMutation,
  useGetContextApiV1AdminPricingContextsContextIdGetQuery,
  useLazyGetContextApiV1AdminPricingContextsContextIdGetQuery,
  useUpdateContextApiV1AdminPricingContextsContextIdPatchMutation,
  useDeactivateContextApiV1AdminPricingContextsContextIdDeleteMutation,
  useFreezeContextApiV1AdminPricingContextsContextIdFreezePostMutation,
  useUnfreezeContextApiV1AdminPricingContextsContextIdUnfreezePostMutation,
  useGetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetQuery,
  useLazyGetContextGlobalValuesApiV1AdminPricingContextsContextIdVariablesValuesGetQuery,
  useSetContextGlobalValueApiV1AdminPricingContextsContextIdVariablesValuesVariableCodePutMutation,
  useListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetQuery,
  useLazyListVersionsApiV1AdminPricingContextsContextIdFormulaVersionsGetQuery,
  useGetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetQuery,
  useLazyGetVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdGetQuery,
  useGetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetQuery,
  useLazyGetDraftApiV1AdminPricingContextsContextIdFormulaDraftGetQuery,
  useUpsertDraftApiV1AdminPricingContextsContextIdFormulaDraftPutMutation,
  useDiscardDraftApiV1AdminPricingContextsContextIdFormulaDraftDeleteMutation,
  usePublishDraftApiV1AdminPricingContextsContextIdFormulaDraftPublishPostMutation,
  useRollbackVersionApiV1AdminPricingContextsContextIdFormulaVersionsVersionIdRollbackPostMutation,
  usePreviewPriceApiV1AdminPricingPreviewPostMutation,
  usePreviewSkuPricingApiV1AdminPricingPreviewSkuPostMutation,
  useGetProfileApiV1AdminPricingProductsProductIdProfileGetQuery,
  useLazyGetProfileApiV1AdminPricingProductsProductIdProfileGetQuery,
  useUpsertProfileApiV1AdminPricingProductsProductIdProfilePutMutation,
  useDeleteProfileApiV1AdminPricingProductsProductIdProfileDeleteMutation,
  useGetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetQuery,
  useLazyGetRequiredVariablesApiV1AdminPricingProductsProductIdProfileRequiredVariablesGetQuery,
  useGetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetQuery,
  useLazyGetSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdGetQuery,
  useUpsertSupplierPricingSettingsApiV1AdminPricingSuppliersSupplierIdPutMutation,
  useListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetQuery,
  useLazyListSupplierTypeContextMappingsApiV1AdminPricingSupplierTypeMappingGetQuery,
  useGetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetQuery,
  useLazyGetSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeGetQuery,
  useUpsertSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypePutMutation,
  useDeleteSupplierTypeContextMappingApiV1AdminPricingSupplierTypeMappingSupplierTypeDeleteMutation,
  useGetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetQuery,
  useLazyGetCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdGetQuery,
  useUpsertCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdPutMutation,
  useDeleteCategoryPricingSettingsApiV1AdminPricingCategoriesCategoryIdContextIdDeleteMutation,
  useRecomputeOneSkuApiV1AdminPricingRecomputeSkusSkuIdPostMutation,
  useRecomputeContextApiV1AdminPricingRecomputeContextsContextIdPostMutation,
  useRecomputeCategoryApiV1AdminPricingRecomputeCategoriesCategoryIdPostMutation,
  useRecomputeSupplierApiV1AdminPricingRecomputeSuppliersSupplierIdPostMutation,
  useGetTrendingProductsApiV1AdminAnalyticsTrendingGetQuery,
  useLazyGetTrendingProductsApiV1AdminAnalyticsTrendingGetQuery,
  useGetSearchAnalyticsApiV1AdminAnalyticsSearchGetQuery,
  useLazyGetSearchAnalyticsApiV1AdminAnalyticsSearchGetQuery,
  useAddItemApiV1CartItemsPostMutation,
  useRemoveItemApiV1CartItemsSkuIdDeleteMutation,
  useUpdateQuantityApiV1CartItemsSkuIdPatchMutation,
  useClearCartApiV1CartDeleteMutation,
  useGetCartApiV1CartGetQuery,
  useLazyGetCartApiV1CartGetQuery,
  useGetCartSummaryApiV1CartSummaryGetQuery,
  useLazyGetCartSummaryApiV1CartSummaryGetQuery,
  useInitiateCheckoutApiV1CartCheckoutPostMutation,
  useConfirmCheckoutApiV1CartCheckoutConfirmPostMutation,
  useCancelCheckoutApiV1CartCheckoutCancelPostMutation,
  useMergeCartsApiV1CartMergePostMutation,
  useCreateAnonymousTokenApiV1CartAnonymousTokenPostMutation,
  useListFavoriteListsApiV1FavoritesListsGetQuery,
  useLazyListFavoriteListsApiV1FavoritesListsGetQuery,
  useCreateFavoriteListApiV1FavoritesListsPostMutation,
  useRenameFavoriteListApiV1FavoritesListsListIdPatchMutation,
  useDeleteFavoriteListApiV1FavoritesListsListIdDeleteMutation,
  useListFavoriteItemsApiV1FavoritesListsListIdItemsGetQuery,
  useLazyListFavoriteItemsApiV1FavoritesListsListIdItemsGetQuery,
  useAddFavoriteItemApiV1FavoritesItemsPostMutation,
  useRemoveFavoriteItemApiV1FavoritesListsListIdItemsTargetTypeTargetIdDeleteMutation,
  useMoveFavoriteItemApiV1FavoritesItemsMovePostMutation,
  useCheckFavoritedApiV1FavoritesCheckPostMutation,
  useRequestUploadApiV1AdminMediaUploadPostMutation,
  useReuploadApiV1AdminMediaStorageObjectIdReuploadPostMutation,
  useConfirmUploadApiV1AdminMediaStorageObjectIdConfirmPostMutation,
  useStreamStatusApiV1AdminMediaStorageObjectIdStatusGetQuery,
  useLazyStreamStatusApiV1AdminMediaStorageObjectIdStatusGetQuery,
  useGetMetadataApiV1AdminMediaStorageObjectIdGetQuery,
  useLazyGetMetadataApiV1AdminMediaStorageObjectIdGetQuery,
  useDeleteMediaApiV1AdminMediaStorageObjectIdDeleteMutation,
  useImportExternalApiV1AdminMediaExternalPostMutation,
  useRequestBackgroundRemovalApiV1AdminMediaStorageObjectIdRemoveBackgroundPostMutation,
  useListPickupPointsApiV1StorefrontLogisticsPickupPointsPostMutation,
  useListProviderAccountsApiV1AdminLogisticsProviderAccountsGetQuery,
  useLazyListProviderAccountsApiV1AdminLogisticsProviderAccountsGetQuery,
  useCreateProviderAccountApiV1AdminLogisticsProviderAccountsPostMutation,
  useGetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetQuery,
  useLazyGetProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdGetQuery,
  useUpdateProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdPutMutation,
  useDeleteProviderAccountApiV1AdminLogisticsProviderAccountsAccountIdDeleteMutation,
  useSetProviderAccountActiveApiV1AdminLogisticsProviderAccountsAccountIdActivePostMutation,
  useRefreshProviderRegistryApiV1AdminLogisticsProviderAccountsRefreshPostMutation,
  useCalculateRatesApiV1AdminLogisticsRatesPostMutation,
  useQuoteForPickupPointApiV1AdminLogisticsRatesQuotePostMutation,
  useListAdminShipmentsApiV1AdminLogisticsShipmentsGetQuery,
  useLazyListAdminShipmentsApiV1AdminLogisticsShipmentsGetQuery,
  useCreateShipmentApiV1AdminLogisticsShipmentsPostMutation,
  useBookShipmentApiV1AdminLogisticsShipmentsShipmentIdBookPostMutation,
  useCancelShipmentApiV1AdminLogisticsShipmentsShipmentIdCancelPostMutation,
  useGetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetQuery,
  useLazyGetShipmentApiV1AdminLogisticsShipmentsShipmentIdGetQuery,
  useGetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetQuery,
  useLazyGetTrackingApiV1AdminLogisticsShipmentsShipmentIdTrackingGetQuery,
  useListPickupPointsApiV1AdminLogisticsPickupPointsPostMutation,
  useListAvailableIntakeDaysApiV1AdminLogisticsIntakesAvailableDaysPostMutation,
  useCreateIntakeApiV1AdminLogisticsShipmentsShipmentIdIntakePostMutation,
  useGetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetQuery,
  useLazyGetIntakeStatusApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdGetQuery,
  useCancelIntakeApiV1AdminLogisticsIntakesProviderCodeProviderIntakeIdDeleteMutation,
  useGetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetQuery,
  useLazyGetDeliveryIntervalsApiV1AdminLogisticsShipmentsShipmentIdDeliveryIntervalsGetQuery,
  useEstimateDeliveryIntervalsApiV1AdminLogisticsDeliveryIntervalsEstimatePostMutation,
  useRegisterClientReturnApiV1AdminLogisticsShipmentsShipmentIdReturnPostMutation,
  useRegisterRefusalApiV1AdminLogisticsShipmentsShipmentIdRefusalPostMutation,
  useCheckReverseAvailabilityApiV1AdminLogisticsReverseAvailabilityPostMutation,
  useGetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetQuery,
  useLazyGetActualDeliveryInfoApiV1AdminLogisticsShipmentsShipmentIdActualDeliveryInfoGetQuery,
  useEditOrderApiV1AdminLogisticsShipmentsShipmentIdEditPostMutation,
  useEditOrderPackagesApiV1AdminLogisticsShipmentsShipmentIdEditPackagesPostMutation,
  useEditOrderItemsApiV1AdminLogisticsShipmentsShipmentIdEditItemsPostMutation,
  useRemoveOrderItemsApiV1AdminLogisticsShipmentsShipmentIdRemoveItemsPostMutation,
  useGetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetQuery,
  useLazyGetEditTaskStatusApiV1AdminLogisticsEditTasksProviderCodeTaskIdGetQuery,
  useEditCdekOrderApiV1AdminLogisticsCdekOrdersEditPostMutation,
  useLookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetQuery,
  useLazyLookupCdekOrderApiV1AdminLogisticsCdekOrdersLookupGetQuery,
  useListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetQuery,
  useLazyListCdekOrderIntakesApiV1AdminLogisticsCdekOrdersOrderUuidIntakesGetQuery,
  useDownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetQuery,
  useLazyDownloadCdekBarcodeApiV1AdminLogisticsCdekShipmentsShipmentIdBarcodeGetQuery,
  useRegisterCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsPostMutation,
  useGetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetQuery,
  useLazyGetCdekDeliveryAgreementApiV1AdminLogisticsCdekDeliveryAgreementsAgreementUuidGetQuery,
  useCreateCdekPrealertApiV1AdminLogisticsCdekPrealertsPostMutation,
  useGetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetQuery,
  useLazyGetCdekPrealertApiV1AdminLogisticsCdekPrealertsPrealertUuidGetQuery,
  useGetCdekChecksApiV1AdminLogisticsCdekChecksGetQuery,
  useLazyGetCdekChecksApiV1AdminLogisticsCdekChecksGetQuery,
  useGetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetQuery,
  useLazyGetCdekRegistriesApiV1AdminLogisticsCdekRegistriesGetQuery,
  useCheckCdekRestrictionsApiV1AdminLogisticsCdekRestrictionsPostMutation,
  useGetCdekReadyPhotosApiV1AdminLogisticsCdekPhotosPostMutation,
  useChangeCdekIntakeStatusApiV1AdminLogisticsCdekIntakesStatusPatchMutation,
  useListCdekTariffsApiV1AdminLogisticsCdekTariffsGetQuery,
  useLazyListCdekTariffsApiV1AdminLogisticsCdekTariffsGetQuery,
  useSuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetQuery,
  useLazySuggestCdekCitiesApiV1AdminLogisticsCdekLocationsSuggestGetQuery,
  useListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetQuery,
  useLazyListCdekCitiesApiV1AdminLogisticsCdekLocationsCitiesGetQuery,
  useListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetQuery,
  useLazyListCdekRegionsApiV1AdminLogisticsCdekLocationsRegionsGetQuery,
  useListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetQuery,
  useLazyListCdekPostalCodesApiV1AdminLogisticsCdekLocationsPostalCodesGetQuery,
  useResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetQuery,
  useLazyResolveCdekLocationByCoordinatesApiV1AdminLogisticsCdekLocationsByCoordinatesGetQuery,
  useListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetQuery,
  useLazyListCdekWebhooksApiV1AdminLogisticsCdekWebhooksGetQuery,
  useCreateCdekWebhookApiV1AdminLogisticsCdekWebhooksPostMutation,
  useSyncCdekWebhooksApiV1AdminLogisticsCdekWebhooksSyncPostMutation,
  useDeleteCdekWebhookApiV1AdminLogisticsCdekWebhooksSubscriptionUuidDeleteMutation,
  useReceiveWebhookApiV1WebhooksLogisticsProviderCodePostMutation,
  useGetPaymentIntentApiV1PaymentsIntentsIntentIdGetQuery,
  useLazyGetPaymentIntentApiV1PaymentsIntentsIntentIdGetQuery,
  useSimulateCaptureApiV1PaymentsIntentsIntentIdSimulateCapturePostMutation,
  useProviderWebhookApiV1WebhooksPaymentsProviderPostMutation,
  useCreateRecipientApiV1RecipientsPostMutation,
  useListMyRecipientsApiV1RecipientsGetQuery,
  useLazyListMyRecipientsApiV1RecipientsGetQuery,
  useGetRecipientApiV1RecipientsRecipientIdGetQuery,
  useLazyGetRecipientApiV1RecipientsRecipientIdGetQuery,
  useUpdateRecipientApiV1RecipientsRecipientIdPatchMutation,
  useArchiveRecipientApiV1RecipientsRecipientIdDeleteMutation,
  useCreateOrderApiV1OrdersPostMutation,
  useListMyOrdersApiV1OrdersGetQuery,
  useLazyListMyOrdersApiV1OrdersGetQuery,
  useGetOrderApiV1OrdersOrderIdGetQuery,
  useLazyGetOrderApiV1OrdersOrderIdGetQuery,
  useGetOrderTrackingApiV1OrdersOrderIdTrackingGetQuery,
  useLazyGetOrderTrackingApiV1OrdersOrderIdTrackingGetQuery,
  useCancelOrderApiV1OrdersOrderIdCancelPostMutation,
  useRefreshRecipientApiV1OrdersOrderIdRefreshRecipientPostMutation,
  useChangePickupPointApiV1OrdersOrderIdPickupPointPatchMutation,
  useAdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetQuery,
  useLazyAdminGetCancellationReasonsMetaApiV1AdminOrdersMetaCancellationReasonsGetQuery,
  useAdminListOrdersApiV1AdminOrdersGetQuery,
  useLazyAdminListOrdersApiV1AdminOrdersGetQuery,
  useAdminGetOrderApiV1AdminOrdersOrderIdGetQuery,
  useLazyAdminGetOrderApiV1AdminOrdersOrderIdGetQuery,
  useAdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetQuery,
  useLazyAdminGetHistoryApiV1AdminOrdersOrderIdHistoryGetQuery,
  useAdminProcureOrderApiV1AdminOrdersOrderIdProcurePostMutation,
  useAdminHoldOrderApiV1AdminOrdersOrderIdHoldPostMutation,
  useAdminResumeOrderApiV1AdminOrdersOrderIdResumePostMutation,
  useAdminForceCancelApiV1AdminOrdersOrderIdForceCancelPostMutation,
  useAdminChangePickupPointApiV1AdminOrdersOrderIdPickupPointPatchMutation,
  useDobropostWebhookApiV1WebhooksDobropostTokenPostMutation,
  useHealthCheckHealthGetQuery,
  useLazyHealthCheckHealthGetQuery,
} = injectedRtkApi;
