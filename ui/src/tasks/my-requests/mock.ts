import { readSession } from '@/shared/api/session';
import { delay, getState, notFound } from '@/shared/mock/store';
import type { MyRequest, RequestListItem } from './types';

export async function listMyRequests(): Promise<RequestListItem[]> {
  await delay();
  const userId = readSession()?.user.id;
  return getState()
    .requests.filter((request) => request.household_id === userId)
    .map((request) => ({
      id: request.id,
      request_code: request.request_code,
      status: request.status,
      monthly_units: request.monthly_units,
      system_kw: request.estimate.system_kw,
      quotes_count: request.quote_count,
      created_at: request.created_at,
    }));
}

export async function getRequest(id: string): Promise<MyRequest> {
  await delay();
  const request = getState().requests.find((item) => item.id === id);
  if (!request || request.household_id !== readSession()?.user.id) notFound();
  return request;
}
