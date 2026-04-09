import ky from 'ky';

export const apiServer = ky.create({
  prefixUrl: process.env.API_BASE_URL ?? '',
  timeout: 10_000,
  retry: {
    limit: 1,
    methods: ['get'],
    statusCodes: [502, 503, 504],
  },
});
