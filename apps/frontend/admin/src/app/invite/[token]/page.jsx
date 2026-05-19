'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { useAcceptInvitation, useInvitationInfo } from '@/entities/staff';
import { useToast } from '@/shared/hooks/useToast';
import { cn } from '@/shared/lib/utils';
import dayjs from '@/shared/lib/dayjs';

const MIN_PASSWORD = 8;
// Backend max-length validation mirrors `apps/backend` — re-checking on
// the client lets us surface a friendly error before the 422 round-trip.
const MAX_PASSWORD = 128;
const MAX_NAME = 100;

// Backend error codes for accept/validate. The map covers every code the
// backend can surface for these public endpoints — anything outside this
// list falls through to the generic "Свяжитесь с администратором" hint.
const ERROR_COPY = {
  INVITATION_NOT_FOUND: {
    title: 'Ссылка недействительна',
    description:
      'Проверьте, что вы открыли актуальную ссылку. Возможно, её обновили.',
  },
  INVITATION_EXPIRED: {
    title: 'Срок действия истёк',
    description: 'Запросите у администратора новую ссылку приглашения.',
  },
  INVITATION_REVOKED: {
    title: 'Приглашение отозвано',
    description: 'Свяжитесь с администратором.',
  },
  INVITATION_ALREADY_ACCEPTED: {
    title: 'Приглашение уже принято',
    description:
      'Войдите по email и паролю, который вы указали при регистрации.',
    cta: { href: '/login', label: 'Войти' },
  },
};

function formatExpiry(value) {
  const m = dayjs(value);
  if (!m.isValid()) return '—';
  return m.format('D MMMM YYYY, HH:mm');
}

export default function InviteAcceptPage() {
  const params = useParams();
  // Next.js gives us `params.token` (string). When the route is opened
  // directly with no token segment (impossible for this matcher but be
  // defensive) the query falls through to the error state.
  const token = typeof params?.token === 'string' ? params.token : '';
  const info = useInvitationInfo(token);

  if (info.isPending) return <InviteSkeleton />;
  if (info.error) return <InviteErrorScreen error={info.error} />;
  return <InviteForm token={token} info={info.data} />;
}

function InviteSkeleton() {
  return (
    <div className="w-full max-w-md animate-pulse rounded-3xl bg-white p-8 shadow-sm">
      <div className="bg-app-card h-6 w-2/3 rounded-md" />
      <div className="mt-6 flex flex-col gap-3">
        <div className="bg-app-card h-12 rounded-lg" />
        <div className="bg-app-card h-12 rounded-lg" />
        <div className="bg-app-card h-12 rounded-lg" />
        <div className="bg-app-card h-12 rounded-lg" />
      </div>
    </div>
  );
}

function InviteErrorScreen({ error }) {
  const code = error?.code ?? 'INVITATION_NOT_FOUND';
  // Backend uses 404 for not-found, 410 for expired/revoked, 422 for
  // already-accepted. The code carries the precise reason — fall back to
  // generic copy if we ever see something new.
  const copy = ERROR_COPY[code] ?? {
    title: 'Не удалось открыть приглашение',
    description: error?.message ?? 'Свяжитесь с администратором.',
  };
  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-8 text-center shadow-sm">
      <h1 className="text-app-text text-xl font-semibold">{copy.title}</h1>
      <p className="text-app-muted mt-3 text-sm">{copy.description}</p>
      {copy.cta && (
        <Link
          href={copy.cta.href}
          className="bg-app-text-dark mt-6 inline-flex items-center justify-center rounded-2xl px-5 py-2.5 text-sm font-medium text-white"
        >
          {copy.cta.label}
        </Link>
      )}
    </div>
  );
}

function InviteForm({ token, info }) {
  const router = useRouter();
  const toast = useToast();
  const accept = useAcceptInvitation(token);

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [touched, setTouched] = useState({});

  const errors = useMemo(() => {
    const out = {};
    if (password.length > 0 && password.length < MIN_PASSWORD) {
      out.password = `Минимум ${MIN_PASSWORD} символов`;
    } else if (password.length > MAX_PASSWORD) {
      out.password = `Максимум ${MAX_PASSWORD} символов`;
    }
    if (confirm.length > 0 && confirm !== password) {
      out.confirm = 'Пароли не совпадают';
    }
    if (firstName.length > MAX_NAME) {
      out.firstName = `Максимум ${MAX_NAME} символов`;
    }
    if (lastName.length > MAX_NAME) {
      out.lastName = `Максимум ${MAX_NAME} символов`;
    }
    return out;
  }, [password, confirm, firstName, lastName]);

  const ready =
    password.length >= MIN_PASSWORD &&
    password.length <= MAX_PASSWORD &&
    password === confirm &&
    firstName.trim().length > 0 &&
    firstName.length <= MAX_NAME &&
    lastName.trim().length > 0 &&
    lastName.length <= MAX_NAME &&
    !accept.isPending;

  function handleSubmit(e) {
    e.preventDefault();
    setTouched({
      password: true,
      confirm: true,
      firstName: true,
      lastName: true,
    });
    if (!ready) return;
    accept.mutate(
      {
        password,
        firstName: firstName.trim(),
        lastName: lastName.trim(),
      },
      {
        onSuccess: () => {
          // BFF wrote httpOnly cookies on 204 — navigation alone is
          // enough to land an authenticated session on /admin.
          toast.success('Добро пожаловать!');
          router.push('/admin');
        },
        onError: (err) => {
          // Race accept ↔ revoke / expiry: backend may flip the state
          // between validate and accept. Show terminal errors as the
          // error screen so the user can act on them.
          if (ERROR_COPY[err?.code]) {
            // Replace the form with the canonical error screen by
            // throwing the form back into "error" mode via toast +
            // refetching validate would also work; we keep it simple
            // with a toast so the user sees what changed.
            toast.error(ERROR_COPY[err.code].title);
            return;
          }
          toast.error(err?.message ?? 'Не удалось принять приглашение');
        },
      },
    );
  }

  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-sm">
      <h1 className="text-app-text text-2xl font-bold">
        Завершите регистрацию
      </h1>
      <p className="text-app-muted mt-2 text-sm">
        Приглашение действительно до {formatExpiry(info?.expiresAt)}
      </p>

      <dl className="bg-app-card mt-5 rounded-2xl px-4 py-3 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-app-muted">Email</dt>
          <dd className="text-app-text font-medium">{info?.email ?? '—'}</dd>
        </div>
        {Array.isArray(info?.roles) && info.roles.length > 0 && (
          <div className="mt-2 flex justify-between gap-3">
            <dt className="text-app-muted">Роли</dt>
            <dd className="text-app-text text-right font-medium">
              {info.roles.join(', ')}
            </dd>
          </div>
        )}
      </dl>

      <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-3">
        <Field
          label="Имя"
          required
          value={firstName}
          onChange={setFirstName}
          onBlur={() => setTouched((t) => ({ ...t, firstName: true }))}
          autoComplete="given-name"
          maxLength={MAX_NAME}
          error={
            touched.firstName && firstName.trim().length === 0
              ? 'Введите имя'
              : touched.firstName
                ? (errors.firstName ?? null)
                : null
          }
        />
        <Field
          label="Фамилия"
          required
          value={lastName}
          onChange={setLastName}
          onBlur={() => setTouched((t) => ({ ...t, lastName: true }))}
          autoComplete="family-name"
          maxLength={MAX_NAME}
          error={
            touched.lastName && lastName.trim().length === 0
              ? 'Введите фамилию'
              : touched.lastName
                ? (errors.lastName ?? null)
                : null
          }
        />
        <Field
          label="Пароль"
          required
          type="password"
          value={password}
          onChange={setPassword}
          onBlur={() => setTouched((t) => ({ ...t, password: true }))}
          autoComplete="new-password"
          maxLength={MAX_PASSWORD}
          helper={`От ${MIN_PASSWORD} до ${MAX_PASSWORD} символов`}
          error={touched.password ? errors.password : null}
        />
        <Field
          label="Повторите пароль"
          required
          type="password"
          value={confirm}
          onChange={setConfirm}
          onBlur={() => setTouched((t) => ({ ...t, confirm: true }))}
          autoComplete="new-password"
          maxLength={MAX_PASSWORD}
          error={touched.confirm ? errors.confirm : null}
        />

        <button
          type="submit"
          disabled={!ready}
          className={cn(
            'bg-app-text-dark mt-3 rounded-2xl px-5 py-3 text-sm font-medium text-white transition-colors',
            !ready && 'cursor-not-allowed opacity-60',
          )}
        >
          {accept.isPending
            ? 'Создаём аккаунт…'
            : 'Принять приглашение и войти'}
        </button>
      </form>
    </div>
  );
}

function Field({
  label,
  required,
  value,
  onChange,
  onBlur,
  error,
  helper,
  type = 'text',
  autoComplete,
  maxLength,
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-app-muted text-xs font-medium">
        {label}
        {required && <span className="text-app-danger ml-1">*</span>}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
        maxLength={maxLength}
        className={cn(
          'border-app-border bg-app-panel text-app-text rounded-lg border px-3 py-2 text-sm transition-colors outline-none',
          'focus:border-app-text',
          error && 'border-app-danger focus:border-app-danger',
        )}
        aria-invalid={error ? true : undefined}
      />
      {error ? (
        <span className="text-app-danger text-xs" role="alert">
          {error}
        </span>
      ) : helper ? (
        <span className="text-app-muted text-xs">{helper}</span>
      ) : null}
    </label>
  );
}
