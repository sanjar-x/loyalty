/**
 * Integration tests for the orders API client.
 *
 * Stubs `global.fetch` directly instead of MSW so we don't grow the dev
 * dependency tree. Each test asserts:
 *   1) the BFF URL/method/body the client sends
 *   2) that a successful response surfaces the JSON body to the caller
 *   3) that backend `{error:{code,message}}` envelopes raise an
 *      `ApiError` with the right code translated through the entity
 *      translation map.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api/clientFetch';

import {
  changePickupPoint,
  createWalkInOrder,
  forceCancelOrder,
  generateIdempotencyKey,
  getOrderById,
  getOrderHistory,
  getOrderTracking,
  holdOrder,
  listOrders,
  procureOrder,
  resumeOrder,
  validateIncomingDeclaration,
} from '../orders';

const ORDER_ID = '019cdbf4-e987-7000-8080-000000000001';

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

describe('orders — read endpoints', () => {
  it('listOrders builds query string with multiple statuses + cursor', async () => {
    const expected = {
      items: [{ orderId: ORDER_ID, orderNumber: 'LOY-1' }],
      nextCursor: null,
    };
    const fetchMock = captureFetch(() => jsonResponse(expected));

    const data = await listOrders({
      statuses: ['paid', 'procured'],
      limit: 25,
      cursor: '2026-05-09T10:00:00Z',
    });

    expect(data).toEqual(expected);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe('GET');
    expect(url).toContain('/api/admin/orders?');
    expect(url).toContain('limit=25');
    expect(url).toContain('cursor=2026-05-09T10%3A00%3A00Z');
    expect(url).toContain('statuses=paid');
    expect(url).toContain('statuses=procured');
  });

  it('getOrderById hits /api/admin/orders/:id', async () => {
    const expected = { orderId: ORDER_ID, status: 'paid' };
    const fetchMock = captureFetch(() => jsonResponse(expected));

    const data = await getOrderById(ORDER_ID);
    expect(data).toEqual(expected);
    expect(fetchMock.mock.calls[0][0]).toBe(`/api/admin/orders/${ORDER_ID}`);
  });

  it('getOrderHistory hits /history', async () => {
    const fetchMock = captureFetch(() => jsonResponse([]));
    const data = await getOrderHistory(ORDER_ID);
    expect(data).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `/api/admin/orders/${ORDER_ID}/history`,
    );
  });

  it('getOrderTracking hits /tracking', async () => {
    const fetchMock = captureFetch(() =>
      jsonResponse({ orderId: ORDER_ID, steps: [] }),
    );
    const data = await getOrderTracking(ORDER_ID);
    expect(data.orderId).toBe(ORDER_ID);
    expect(fetchMock.mock.calls[0][0]).toBe(
      `/api/admin/orders/${ORDER_ID}/tracking`,
    );
  });

  it('translates ORDER_NOT_FOUND into Russian message', async () => {
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'ORDER_NOT_FOUND',
            message: 'Order not found',
            details: {},
          },
        },
        { status: 404 },
      ),
    );

    await expect(getOrderById(ORDER_ID)).rejects.toMatchObject({
      name: 'ApiError',
      code: 'ORDER_NOT_FOUND',
      status: 404,
      message: 'Заказ не найден',
    });
  });
});

describe('orders — write endpoints', () => {
  it('procureOrder POSTs incomingDeclaration', async () => {
    const fetchMock = captureFetch(() => noContentResponse());
    await procureOrder(ORDER_ID, { incomingDeclaration: 'CN-12-AB-9876' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/orders/${ORDER_ID}/procure`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      incomingDeclaration: 'CN-12-AB-9876',
    });
  });

  it('holdOrder POSTs reason', async () => {
    const fetchMock = captureFetch(() => noContentResponse());
    await holdOrder(ORDER_ID, { reason: 'manager_review' });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/orders/${ORDER_ID}/hold`);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ reason: 'manager_review' });
  });

  it('resumeOrder POSTs without body', async () => {
    const fetchMock = captureFetch(() => noContentResponse());
    await resumeOrder(ORDER_ID);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/orders/${ORDER_ID}/resume`);
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });

  it('forceCancelOrder POSTs reason + idempotencyKey', async () => {
    const fetchMock = captureFetch(() => noContentResponse());
    await forceCancelOrder(ORDER_ID, {
      reason: 'customer_changed_mind',
      idempotencyKey: 'idempotency-12345678',
    });
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body)).toEqual({
      reason: 'customer_changed_mind',
      idempotencyKey: 'idempotency-12345678',
    });
  });

  it('changePickupPoint PATCHes carrier + pointId', async () => {
    const fetchMock = captureFetch(() => noContentResponse());
    await changePickupPoint(ORDER_ID, {
      carrier: 'cdek',
      pointId: 'CDEK-MSK-001',
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/admin/orders/${ORDER_ID}/pickup-point`);
    expect(init.method).toBe('PATCH');
    expect(JSON.parse(init.body)).toEqual({
      carrier: 'cdek',
      pointId: 'CDEK-MSK-001',
    });
  });

  it('createWalkInOrder POSTs the payload verbatim and returns 201 body', async () => {
    const payload = {
      profile: { fullName: 'Иван Иванов', phone: '+79108897762' },
      recipient: {
        fullNameRu: 'Иванов Иван',
        fullNameLat: 'Ivanov Ivan',
        phone: '+79108897762',
        email: 'ivan@example.com',
        passportSerial: '1234',
        passportNumber: '567890',
        passportIssueDate: '2015-05-22',
        birthDate: '1990-01-01',
        inn: '500100732272',
      },
      items: [{ skuId: '7c9e6679-7425-40de-944b-e07fc1f90ae7', quantity: 2 }],
      pickupCarrier: 'cdek',
      pickupPointId: 'MSK-1',
      currency: 'RUB',
      payment: { method: 'cash', reference: 'POS-12345' },
      idempotencyKey: 'idem-form-mount-uuid-v4',
      deliveryAmount: 0,
    };
    const fetchMock = captureFetch(() =>
      jsonResponse(
        {
          orderId: ORDER_ID,
          identityId: '7037ab70-f87f-441b-8f92-28d6bb8760a5',
          totalAmount: 25000,
          currency: 'RUB',
        },
        { status: 201 },
      ),
    );

    const result = await createWalkInOrder(payload);

    expect(result).toMatchObject({ orderId: ORDER_ID, totalAmount: 25000 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/admin/orders');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual(payload);
  });

  it('translates WALK_IN_SKU_NOT_USABLE — caller still gets details for field highlighting', async () => {
    const details = {
      missing: [],
      inactive: [],
      unpriced: ['7c9e6679-7425-40de-944b-e07fc1f90ae7'],
      currencyMismatch: [],
    };
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'WALK_IN_SKU_NOT_USABLE',
            message: 'Walk-in order references unusable SKUs',
            details,
          },
        },
        { status: 422 },
      ),
    );

    await expect(createWalkInOrder({})).rejects.toMatchObject({
      name: 'ApiError',
      code: 'WALK_IN_SKU_NOT_USABLE',
      status: 422,
      // toast-level translation is set, but the mutation hook reads
      // err.details to drive per-line highlighting — assert both are
      // preserved.
      message: expect.stringContaining('недоступны для walk-in'),
      details,
    });
  });

  it('translates ORDER_INVALID_TRANSITION on a write 422', async () => {
    captureFetch(() =>
      jsonResponse(
        {
          error: {
            code: 'ORDER_INVALID_TRANSITION',
            message: 'Invalid transition',
            details: {},
          },
        },
        { status: 422 },
      ),
    );

    await expect(
      holdOrder(ORDER_ID, { reason: 'manager_review' }),
    ).rejects.toBeInstanceOf(ApiError);
    await expect(
      holdOrder(ORDER_ID, { reason: 'manager_review' }),
    ).rejects.toMatchObject({
      code: 'ORDER_INVALID_TRANSITION',
      status: 422,
      message: expect.stringContaining('Действие недоступно'),
    });
  });
});

describe('orders — local validation helpers', () => {
  it('validateIncomingDeclaration accepts the documented charset', () => {
    expect(validateIncomingDeclaration('CN-12-AB-9876')).toBe(true);
    expect(validateIncomingDeclaration('A')).toBe(true);
  });

  it('validateIncomingDeclaration rejects forbidden chars and overflow', () => {
    expect(validateIncomingDeclaration('')).toBe(false);
    expect(validateIncomingDeclaration('CN_under_score')).toBe(false);
    expect(validateIncomingDeclaration('CN with space')).toBe(false);
    expect(validateIncomingDeclaration('A'.repeat(16))).toBe(false);
  });

  it('generateIdempotencyKey returns a string within backend bounds', () => {
    const key = generateIdempotencyKey();
    expect(typeof key).toBe('string');
    expect(key.length).toBeGreaterThanOrEqual(8);
    expect(key.length).toBeLessThanOrEqual(128);
  });
});
