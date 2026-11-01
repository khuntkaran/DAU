import { delay, getState } from '@/shared/mock/store';
import type { RoofAssessment } from './types';

export async function getAssessment(requestId: string): Promise<RoofAssessment> {
  await delay();
  const found = getState().assessments[requestId];
  if (!found) {
    return {
      status: 'failed',
      photo_url: null,
      usable_area_sqm: null,
      max_kw_by_area: null,
      shade_risk: null,
      summary: null,
      obstructions: [],
    };
  }
  const { ready_at: readyAt, ...assessment } = found;
  return { ...assessment, status: Date.now() >= readyAt ? 'done' : 'pending' };
}
