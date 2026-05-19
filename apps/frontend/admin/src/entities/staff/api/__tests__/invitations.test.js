/**
 * Integration tests for the invitations API client. Pattern lifted from
 * `entities/order/api/__tests__/orders.test.js` (stub global fetch
 * + assert URL/method/body shape).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api/clientFetch';

import {
  acceptInvitationToken,
  createInvitation,
  fetchInvitations,
  resendInvitation,
  revokeInvitation,
  validateInvitationToken,
} from '../invitations';

const INVITATION_ID = '019cdbf4-e987-7000-8080-000000000001';
const TOKEN = 'sha256-test-token-abc123';

function jsonResponse(body, init = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'Content-Type': 'application/json', ...init.headers },
  });
}

function noContentResponse() {
  return new Response(null, { status: 204 });
}

function captureFetch(impl) {
  const fetchMock = vi.fn(impl);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('invitations.api — admin endpoints', () => {
  it('fetchInvitations builds offset/limit/status query', async () => {
    const fetchMock = captureFetch(() =>
      jsonResponse({ items: [], total: 0, offset: 0, limit: 20 }),
    );

    await fetchInvitations({ page: 2, limit: 10, status: 'PENDING' });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/admin/staff/invitations?');
    expect(url).toContain('offset=10');
    expect(url).toContain('limit=10');
    expect(url).toContain('status=PENDING');
  });

  it('fetchInvitations normalises malformed response to safe defaults', async () => {
    captureFetch(() => jsonResponse({}));
    const data = await fetchInvitations();
    expect(data).toEqual({ items: [], total: 0, offset: 0, limit: 20 });
  });

  it('createInvitation POSTs payload', async () => {
    const fetchMock = captureFetch(() =>
      jsonResponse(
        { invitationId: INVITATION_ID, inviteUrl: 'https://x/invite/xyz' },
        { status: 201 },
      ),
    );

    const result = await createInvitation({
      email: 'new@example.com',
      roleIds: ['role-1'],
    });

    expect(result.invitationId).toBe(INVITATION_ID);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/admin/staff/invitations');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      email: 'new@example.com',
      roleIds: ['role-1'],
    });
  });

  it('resendInvitation POSTs without body and returns new {invitationId, inviteUrl}', async () => {
    const fetchMock = captureFetch(() =>
      jsonResponse(
        { invitationId: 'new-id', inviteUrl: 'https://x/invite/new' },
        { status: 201 },
      ),
    );

    const result = await resendInvitation(INVITATION_ID);

    expect(result.invitationId).toBe('new-id');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/staff/invitations/${INVITATION_ID}/resend`);
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });

  it('revokeInvitation DELETEs the invitation', async () => {
    const fetchMock = captureFetch(() => noContentResponse());

    await revokeInvitation(INVITATION_ID);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/staff/invitations/${INVITATION_ID}`);
    expect(init.method).toBe('DELETE');
  });

  it('createInvitation surfaces backend error code via ApiError', async () => {
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'ACTIVE_INVITATION_EXISTS',
            message: 'Active invitation exists',
            details: {},
          },
        },
        { status: 409 },
      ),
    );

    await expect(
      createInvitation({ email: 'dup@example.com', roleIds: ['role-1'] }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      code: 'ACTIVE_INVITATION_EXISTS',
      status: 409,
    });
  });
});

describe('invitations.api — public endpoints', () => {
  it('validateInvitationToken GETs /api/invitations/{token}/validate', async () => {
    const fetchMock = captureFetch(() =>
      jsonResponse({
        email: 'new@example.com',
        roles: ['manager'],
        expiresAt: '2026-05-19T14:32:00Z',
      }),
    );

    const data = await validateInvitationToken(TOKEN);

    expect(data.email).toBe('new@example.com');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/invitations/${encodeURIComponent(TOKEN)}/validate`);
    expect(init.method).toBe('GET');
  });

  it('validateInvitationToken propagates 410 as ApiError with INVITATION_EXPIRED code', async () => {
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'INVITATION_EXPIRED',
            message: 'Invitation has expired',
            details: {},
          },
        },
        { status: 410 },
      ),
    );

    await expect(validateInvitationToken(TOKEN)).rejects.toMatchObject({
      name: 'ApiError',
      code: 'INVITATION_EXPIRED',
      status: 410,
    });
  });

  it('acceptInvitationToken POSTs payload to /api/invitations/{token}/accept', async () => {
    const fetchMock = captureFetch(() => noContentResponse());

    const payload = {
      password: 'super-strong-pass',
      firstName: 'Иван',
      lastName: 'Петров',
    };
    const result = await acceptInvitationToken(TOKEN, payload);

    expect(result).toBeNull();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/invitations/${encodeURIComponent(TOKEN)}/accept`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual(payload);
  });

  it('acceptInvitationToken raises ApiError on backend rejection', async () => {
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'INVITATION_ALREADY_ACCEPTED',
            message: 'Already accepted',
            details: {},
          },
        },
        { status: 422 },
      ),
    );

    await expect(
      acceptInvitationToken(TOKEN, {
        password: 'x',
        firstName: 'A',
        lastName: 'B',
      }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});
