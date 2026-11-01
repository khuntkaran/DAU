/** HTTP client for the real API. Each task's api.ts maps its responses to UI types. */
import { readSession, writeSession } from './session';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

/** Tests set this to mock. Everything else talks to the real API. */
export const IS_MOCK = process.env.NEXT_PUBLIC_API_MODE === 'mock';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH';
  body?: unknown;
}

function authHeaders(): Record<string, string> {
  const session = readSession();
  return session ? { Authorization: `Bearer ${session.token}` } : {};
}

async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach the server.');
  }
  if (response.ok) return response;

  const payload = (await response.json().catch(() => null)) as {
    error?: { code?: string; message?: string };
  } | null;
  const code = payload?.error?.code ?? 'request_failed';
  // An expired token cannot recover, so return to sign-in instead of failing page by page.
  if (response.status === 401 && code === 'invalid_token') writeSession(null);
  throw new ApiError(
    response.status,
    code,
    payload?.error?.message ?? `Request failed with status ${response.status}.`,
  );
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isForm = options.body instanceof FormData;
  const headers = authHeaders();
  if (options.body !== undefined && !isForm) headers['Content-Type'] = 'application/json';

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) body = options.body;
  else if (options.body !== undefined) body = JSON.stringify(options.body);

  const response = await send(path, { method: options.method ?? 'GET', headers, body });
  return (await response.json()) as T;
}

interface Page<T> {
  items: T[];
  next_cursor?: string | null;
}

/** Follows cursors to the end, because the screens show complete lists. */
export async function fetchAllPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null | undefined;
  do {
    const separator = path.includes('?') ? '&' : '?';
    const suffix = cursor ? `${separator}cursor=${encodeURIComponent(cursor)}` : '';
    const page = await apiRequest<Page<T>>(`${path}${suffix}`);
    items.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return items;
}

/** Files need the login token, which an img tag cannot send, so they load as blobs. */
export async function fetchFileUrl(path: string): Promise<string> {
  const response = await send(path, { headers: authHeaders() });
  return URL.createObjectURL(await response.blob());
}
