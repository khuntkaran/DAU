import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { Recommendation } from './types';

export function getRecommendation(requestId: string): Promise<Recommendation> {
  return IS_MOCK
    ? mock.getRecommendation(requestId)
    : apiRequest(`/requests/${requestId}/recommendation`, { method: 'POST' });
}
