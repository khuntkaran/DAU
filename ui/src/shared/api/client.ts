/** HTTP client for the real API. Each task's api.ts picks this or its mock. */
import { readSession } from './session';

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
export const IS_MOCK = (process.env.NEXT_PUBLIC_API_MODE ?? 'mock') !== 'live';

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

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const session = readSession();
  const isForm = options.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (session) headers.Authorization = `Bearer ${session.token}`;
  if (options.body !== undefined && !isForm) headers['Content-Type'] = 'application/json';

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) body = options.body;
  else if (options.body !== undefined) body = JSON.stringify(options.body);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { method: options.method ?? 'GET', headers, body });
  } catch {
    throw new ApiError(0, 'network_error', 'Could not reach the server.');
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { code?: string; message?: string };
    } | null;
    throw new ApiError(
      response.status,
      payload?.error?.code ?? 'request_failed',
      payload?.error?.message ?? `Request failed with status ${response.status}.`,
    );
  }
  return (await response.json()) as T;
}
