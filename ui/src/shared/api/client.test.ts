import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiRequest } from './client';
import { writeSession } from './session';

function respondWith(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('apiRequest', () => {
  it('returns parsed JSON', async () => {
    vi.stubGlobal('fetch', respondWith(200, { ok: true }));
    await expect(apiRequest('/health')).resolves.toEqual({ ok: true });
  });

  it('sends the session token', async () => {
    const fetchMock = respondWith(200, {});
    vi.stubGlobal('fetch', fetchMock);
    writeSession({
      token: 'abc',
      user: { id: 'u', role: 'vendor', full_name: 'V', phone: '1', preferred_lang: 'en' },
    });
    await apiRequest('/requests/mine');
    const init = fetchMock.mock.calls[0]?.at(1) as unknown as RequestInit;
    expect(init.headers).toMatchObject({ Authorization: 'Bearer abc' });
  });

  it('turns the error envelope into an ApiError', async () => {
    vi.stubGlobal('fetch', respondWith(409, { error: { code: 'already_accepted', message: 'Taken' } }));
    await expect(apiRequest('/quotes/1/accept', { method: 'POST' })).rejects.toMatchObject({
      status: 409,
      code: 'already_accepted',
      message: 'Taken',
    });
  });

  it('reports a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    const error = await apiRequest('/health').catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe('network_error');
  });
});
