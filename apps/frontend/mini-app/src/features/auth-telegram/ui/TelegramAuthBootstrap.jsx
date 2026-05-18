'use client';

import { useEffect, useRef } from 'react';

import { useTelegram, useAuthStore, AuthStatus } from '@/entities/user';
import { onAuthExpired } from '@/shared/lib/events';
import { isBrowserDebugAuthEnabled } from '@/features/auth-telegram/lib/debug';
import { api } from '@/app/providers/store/instance';
import { useAppDispatch } from '@/shared/api/base-api/hooks';
import { getAnonymousToken, clearAnonymousToken } from '@/shared/lib/anonymous-token';

/**
 * TelegramAuthBootstrap — renderless component (returns null).
 *
 * When isReady === true AND authStatus === 'idle' | 'expired' → automatically starts auth.
 * Deduplication: inFlightSourceRef and failedSourceRef prevent duplicate requests
 * with the same initData.
 */
export default function TelegramAuthBootstrap() {
  const { initData, isReady, user: tgUser } = useTelegram();
  const { status, authStart, authSuccess, authFailure, sessionExpired, setVerifying } =
    useAuthStore();
  const dispatch = useAppDispatch();

  const inFlightSourceRef = useRef(null);
  const failedSourceRef = useRef(null);
  const lastAttemptAtRef = useRef(0);
  const attemptCountRef = useRef(0);
  const verifiedRef = useRef(false);

  // Minimum interval between auth attempts to prevent 401→refresh→expired→reauth loops
  const AUTH_COOLDOWN_MS = 30_000;
  const MAX_ATTEMPTS = 3;

  // Auth expiry event listener
  useEffect(() => {
    return onAuthExpired(() => {
      sessionExpired();
    });
  }, [sessionExpired]);

  /**
   * Soft validation — when `AUTHENTICATED` is restored from persist, quickly
   * verify that the cookie is actually valid.
   *
   * Runs only **once** per Telegram session (via `sessionStorage`). This
   * prevents re-validation on full-page reload (back from product, navigating
   * between pages) → no splash flash.
   *
   * Fail-safe timeout: if `/me` doesn't respond within 6 seconds, we call
   * `setVerifying(false)` and open the children. Network slowness (cloudflare
   * tunnel + Railway cold start) shouldn't block the UI forever — when RTK
   * Query receives 401 it will restart the auth flow on its own.
   */
  useEffect(() => {
    if (verifiedRef.current) return;
    if (status !== AuthStatus.AUTHENTICATED) return;

    // Per-tab session — we don't re-validate on every full reload.
    // (We avoid `localStorage`: when the cookie expires and the tab is closed,
    //  on the next tab open we re-validate.)
    let cachedAt = null;
    try {
      cachedAt = window.sessionStorage?.getItem('lm-auth-verified-at') ?? null;
    } catch {
      // If we can't access sessionStorage — invalidate the cache.
    }
    const VERIFY_TTL_MS = 5 * 60 * 1000; // 5 minutes
    const isFresh = cachedAt && Date.now() - Number(cachedAt) < VERIFY_TTL_MS;

    verifiedRef.current = true;

    if (isFresh) {
      // Recently verified — don't show splash, render immediately.
      return;
    }

    setVerifying(true);

    let cancelled = false;
    const FETCH_TIMEOUT_MS = 6000;
    const timeoutId = setTimeout(() => {
      if (cancelled) return;
      // No response within 6s — open the children, when the network recovers
      // and RTK Query gets a 401, auth will be retried.
      setVerifying(false);
    }, FETCH_TIMEOUT_MS);

    fetch('/api/backend/api/v1/profile/me', {
      method: 'GET',
      credentials: 'include',
      headers: { accept: 'application/json' },
    })
      .then(async (res) => {
        if (cancelled) return;
        clearTimeout(timeoutId);
        if (res.ok) {
          // Cookie valid — seed the response into the RTK Query cache, so
          // that when profile/settings pages open `useGetMeQuery` doesn't
          // re-fetch. We re-execute the `transformResponse` logic here
          // (camelCase → snake_case aliases).
          try {
            const data = await res.json();
            const normalized = {
              ...data,
              first_name: data?.firstName,
              last_name: data?.lastName,
              photo_url: data?.photoUrl || null,
            };
            // RTKQ endpoint name comes from codegen — the long
            // `getMyProfileApiV1ProfileMeGet` (hooks.js aliases
            // useGetMeQuery → useGetMyProfileApiV1ProfileMeGetQuery, but the
            // endpoint's string name is the codegen name). Previously this
            // read 'getMe' — a silent error in the endpoint registry, the
            // cache was never seeded.
            dispatch(
              api.util.upsertQueryData(
                'getMyProfileApiV1ProfileMeGet',
                undefined,
                normalized
              )
            );
          } catch (err) {
            // JSON parse error or dispatch error — seed is skipped
            // (useGetMeQuery will re-fetch on its own), but it's still
            // visible in the baseline.
            console.warn('[auth/soft-verify] profile seed failed', err?.message);
          }
          try {
            window.sessionStorage?.setItem('lm-auth-verified-at', String(Date.now()));
          } catch {
            // No sessionStorage — we'll re-verify on the next reload.
          }
          setVerifying(false);
          return;
        }
        // 401/403 — token expired. `sessionExpired` moves status to
        // `EXPIRED` + sets `isVerifying: false`; the bootstrap effect below
        // re-authenticates with initData.
        try {
          window.sessionStorage?.removeItem('lm-auth-verified-at');
        } catch {
          /* noop */
        }
        sessionExpired();
      })
      .catch(() => {
        if (cancelled) return;
        clearTimeout(timeoutId);
        // Network error — optimistically open the children (RTK Query
        // will retry on its own later).
        setVerifying(false);
      });

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [status, setVerifying, sessionExpired, dispatch]);

  // Auto-auth trigger
  useEffect(() => {
    if (!isReady) return;
    if (status !== AuthStatus.IDLE && status !== AuthStatus.EXPIRED) return;

    const source = initData || '';
    const isDebug = !source && isBrowserDebugAuthEnabled();

    // The Telegram SDK was not found AND debug mode is not enabled — this
    // usually happens when the user opens the Mini App in a plain mobile
    // browser. To avoid an endless splash, we move to the ERROR state;
    // `AuthGate` shows the user a "Open via Telegram" message.
    if (!source && !isDebug) {
      authFailure('OPEN_IN_TELEGRAM');
      return;
    }

    const sourceKey = source || '__debug__';

    // Deduplication — request already in flight or previously failed
    if (inFlightSourceRef.current === sourceKey) return;
    if (failedSourceRef.current === sourceKey && status !== AuthStatus.EXPIRED) return;

    // Cooldown & max attempts — prevents the 401→refresh→expired→reauth loop
    const now = Date.now();
    if (lastAttemptAtRef.current > 0 && now - lastAttemptAtRef.current < AUTH_COOLDOWN_MS) {
      return;
    }
    if (attemptCountRef.current >= MAX_ATTEMPTS) {
      return;
    }
    lastAttemptAtRef.current = now;
    attemptCountRef.current += 1;

    inFlightSourceRef.current = sourceKey;
    authStart();

    fetch('/api/auth/telegram', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ initData: source || undefined }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data?.error || `Auth failed: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        inFlightSourceRef.current = null;
        failedSourceRef.current = null;
        attemptCountRef.current = 0; // reset on success
        authSuccess({
          isNewUser: data?.isNewUser ?? false,
          user: tgUser
            ? {
                firstName: tgUser.first_name || '',
                lastName: tgUser.last_name || '',
                photoUrl: tgUser.photo_url || '',
                tgId: tgUser.id || null,
              }
            : null,
        });

        // Spec §7.3: if an anonymous cart token exists, after successful login
        // merge the guest cart with the authenticated cart.
        // On error skip silently — this is best-effort and shouldn't halt
        // the main auth flow. The token is cleared in any case (to prevent
        // repeated merge attempts and CONFLICTs in later sessions with the
        // old token).
        const anonToken = getAnonymousToken();
        if (anonToken) {
          // Codegen exports the endpoint as `mergeCartsApiV1CartMergePost`
          // (see shared/api/codegen/api.ts:2601). Previously this was
          // `api.endpoints.mergeCart` — `undefined` → TypeError, which was
          // swallowed by `.catch(() => null)`. Result: anonymous→auth
          // cart merge never worked (caught during code review on
          // refactor/mini-app-fsd).
          dispatch(
            api.endpoints.mergeCartsApiV1CartMergePost.initiate({
              mergeCartRequest: { anonymousToken: anonToken },
            })
          )
            .unwrap()
            .catch((err) => {
              // best-effort merge — don't block auth, but log it
              console.error('[auth] cart merge failed', err);
              return null;
            })
            .finally(() => {
              clearAnonymousToken();
              // Cart cache invalidate — even if the merge failed, the new access
              // will reveal the real cart state.
              dispatch(api.util.invalidateTags(['Cart']));
            });
        }

        // RTK Query cache invalidate
        dispatch(api.util.invalidateTags(['User', 'Referrals']));
      })
      .catch((err) => {
        inFlightSourceRef.current = null;
        failedSourceRef.current = sourceKey;
        authFailure(err?.message || 'Auth failed');
      });
  }, [isReady, initData, status, authStart, authSuccess, authFailure, dispatch]);

  return null;
}
