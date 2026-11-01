import { readSession } from '@/shared/api/session';
import { delay, getState, notFound } from '@/shared/mock/store';
import type { MyRequest } from './types';

export async function listMyRequests(): Promise<MyRequest[]> {
  await delay();
  const userId = readSession()?.user.id;
  return getState().requests.filter((request) => request.household_id === userId);
}

export async function getRequest(id: string): Promise<MyRequest> {
  await delay();
  const request = getState().requests.find((item) => item.id === id);
  if (!request || request.household_id !== readSession()?.user.id) notFound();
  return request;
}
