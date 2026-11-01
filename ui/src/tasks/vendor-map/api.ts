import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { BoundingBox, OpenRequest } from './types';

export function listOpenRequests(box: BoundingBox): Promise<OpenRequest[]> {
  if (IS_MOCK) return mock.listOpenRequests(box);
  const bbox = [box.south, box.west, box.north, box.east].join(',');
  return apiRequest(`/requests/open?bbox=${encodeURIComponent(bbox)}`);
}
