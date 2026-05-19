export const geoKeys = {
  all: ['geo'],
  countries: ({ lang, limit }) => [
    ...geoKeys.all,
    'countries',
    { lang, limit },
  ],
  subdivisions: ({ countryCode, lang }) => [
    ...geoKeys.all,
    'subdivisions',
    { countryCode, lang },
  ],
};
