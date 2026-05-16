'use client';

import { useEffect, useRef } from 'react';

import { useTelegram } from '@/lib/features/telegram/provider';
import { useAuthStore } from '@/lib/features/auth/store';
import { AuthStatus } from '@/lib/features/auth/types';
import { onAuthExpired } from '@/lib/auth-events';
import { isBrowserDebugAuthEnabled } from '@/lib/features/auth/lib/debug';
import { api } from '@/lib/store/api';
import { useAppDispatch } from '@/lib/store/hooks';
import { getAnonymousToken, clearAnonymousToken } from '@/lib/cart/anonymousToken';

/**
 * TelegramAuthBootstrap — renderless component (returns null).
 *
 * isReady === true VA authStatus === 'idle' | 'expired' bo'lsa → avtomatik auth boshlaydi.
 * Deduplication: inFlightSourceRef va failedSourceRef orqali bir xil initData bilan
 * takroriy so'rov yuborilmaydi.
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
   * Soft validation — persist'dan `AUTHENTICATED` tiklanganda cookie haqiqatda
   * valid ekanligini tezkor tekshirish.
   *
   * Bir Telegram sessiyasida faqat **bir marta** ishlaydi (`sessionStorage`
   * orqali). Bu full-page reload (productdan back, har sahifaga o'tish)
   * paytida qayta verification chaqirilishini oldini oladi → splash flash yo'q.
   *
   * Fail-safe timeout: 6 soniya ichida `/me` javob kelmasa `setVerifying(false)`
   * qilib children'ni ochamiz. Tarmoq sekinligi (cloudflare tunnel + Railway
   * cold start) UI'ni mangu blok qilmasligi kerak — RTK Query 401 kelganda
   * o'zi auth flow'ni qayta boshlaydi.
   */
  useEffect(() => {
    if (verifiedRef.current) return;
    if (status !== AuthStatus.AUTHENTICATED) return;

    // Per-tab sessiya uchun — har full reload'da qayta tekshirilmaydi.
    // (`localStorage` qilmaymiz: cookie tugashida tab yopilsa, keyingi tab
    //  ochilganda qayta validate qilamiz.)
    let cachedAt = null;
    try {
      cachedAt = window.sessionStorage?.getItem('lm-auth-verified-at') ?? null;
    } catch {
      // sessionStorage'ga kira olmasak — cache'ni inkor qilamiz.
    }
    const VERIFY_TTL_MS = 5 * 60 * 1000; // 5 daqiqa
    const isFresh = cachedAt && Date.now() - Number(cachedAt) < VERIFY_TTL_MS;

    verifiedRef.current = true;

    if (isFresh) {
      // Yaqinda verifyed — splash ko'rsatmaymiz, darhol render.
      return;
    }

    setVerifying(true);

    let cancelled = false;
    const FETCH_TIMEOUT_MS = 6000;
    const timeoutId = setTimeout(() => {
      if (cancelled) return;
      // 6s ichida javob yo'q — children'ni ochamiz, tarmoq tiklanganda RTK
      // Query 401 olsa qayta auth qilinadi.
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
          // Cookie valid — javobni RTK Query cache'ga seed qilamiz, shunda
          // profile/settings sahifalari ochilganda `useGetMeQuery` qayta
          // fetch qilmaydi. `transformResponse` logikasini shu yerda qayta
          // bajaramiz (camelCase → snake_case aliases).
          try {
            const data = await res.json();
            const normalized = {
              ...data,
              first_name: data?.firstName,
              last_name: data?.lastName,
              photo_url: data?.photoUrl || null,
            };
            dispatch(api.util.upsertQueryData('getMe', undefined, normalized));
          } catch {
            // JSON parse xatosi — seed o'tkazib yuboriladi.
          }
          try {
            window.sessionStorage?.setItem('lm-auth-verified-at', String(Date.now()));
          } catch {
            // sessionStorage yo'q — keyingi reload'da qayta verify qilamiz.
          }
          setVerifying(false);
          return;
        }
        // 401/403 — token expired. `sessionExpired` status'ni `EXPIRED`'ga
        // o'tkazadi + `isVerifying: false` qiladi; bootstrap pastdagi effect
        // initData bilan qayta auth qiladi.
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
        // Tarmoq xatosi — optimistik tarzda children'ni ochamiz (RTK Query
        // o'zi keyin qayta urinadi).
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

    // Telegram SDK topilmadi VA debug rejim ham yoqilmagan — bu odatda
    // foydalanuvchi Mini App'ni oddiy mobil brauzerdan ochganida sodir
    // bo'ladi. Mangu splash'ni oldini olish uchun ERROR holatiga o'tkazamiz;
    // `AuthGate` foydalanuvchiga "Telegram orqali oching" xabarini ko'rsatadi.
    if (!source && !isDebug) {
      authFailure('OPEN_IN_TELEGRAM');
      return;
    }

    const sourceKey = source || '__debug__';

    // Deduplication — allaqachon yuborilgan yoki xato bo'lgan so'rov
    if (inFlightSourceRef.current === sourceKey) return;
    if (failedSourceRef.current === sourceKey && status !== AuthStatus.EXPIRED) return;

    // Cooldown & max attempts — 401→refresh→expired→reauth loopni oldini olish
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

        // Spec §7.3: anonymous cart token mavjud bo'lsa, login muvaffaqiyatli
        // bo'lganidan keyin guest savatni authenticated savat bilan birlashtirish.
        // Xato bo'lsa silently skip — bu best-effort, asosiy auth flow'ni
        // to'xtatmasligi kerak. Token har holatda tozalanadi (qayta merge
        // urinishlarini va eski token bilan keyingi sessiyalarda
        // CONFLICT'lardan saqlanish).
        const anonToken = getAnonymousToken();
        if (anonToken) {
          dispatch(api.endpoints.mergeCart.initiate({ anonymousToken: anonToken }))
            .unwrap()
            .catch(() => null)
            .finally(() => {
              clearAnonymousToken();
              // Cart cache'ni yangilash — invalidatesTags allaqachon mergeCart
              // mutation'ida bor, lekin mergeCart fail bo'lsa ham cart'ni
              // refetch qilamiz, yangi access bo'yicha haqiqiy holat keladi.
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
