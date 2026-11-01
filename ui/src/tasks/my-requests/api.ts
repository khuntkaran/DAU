import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { MyRequest } from './types';

export function listMyRequests(): Promise<MyRequest[]> {
  return IS_MOCK ? mock.listMyRequests() : apiRequest('/requests/mine');
}

export function getRequest(id: string): Promise<MyRequest> {
  return IS_MOCK ? mock.getRequest(id) : apiRequest(`/requests/${id}`);
}
