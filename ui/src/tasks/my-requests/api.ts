import { apiRequest, fetchAllPages, IS_MOCK } from '@/shared/api/client';
import { toSolarRequest } from '@/shared/api/mappers';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { MyRequest, RequestListItem } from './types';

export async function listMyRequests(): Promise<RequestListItem[]> {
  if (IS_MOCK) return mock.listMyRequests();
  const items = await fetchAllPages<Schemas['RequestSummary']>('/requests/mine');
  return items.map((item) => ({ ...item, system_kw: Number(item.system_kw) }));
}

export async function getRequest(id: string): Promise<MyRequest> {
  if (IS_MOCK) return mock.getRequest(id);
  return toSolarRequest(await apiRequest<Schemas['RequestOut']>(`/requests/${id}`));
}
