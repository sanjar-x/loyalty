/**
 * Sprint 3d: User RTKQ hooks — split out from app/providers/store/hooks.
 *
 * The `enhancedApi` source stays in app/providers/store/instance.js
 * (endpoint assembly via enhanceEndpoints). Further refactoring into
 * shared/api/store/ is a separate iteration.
 */
import { enhancedApi } from '@/app/providers/store/instance';

export const useGetMeQuery = enhancedApi.useGetMyProfileApiV1ProfileMeGetQuery;
