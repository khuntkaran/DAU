import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { RoofAssessment } from './types';

export function getAssessment(requestId: string): Promise<RoofAssessment> {
  return IS_MOCK ? mock.getAssessment(requestId) : apiRequest(`/requests/${requestId}/assessment`);
}
