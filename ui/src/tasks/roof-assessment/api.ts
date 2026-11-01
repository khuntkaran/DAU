import { apiRequest, fetchFileUrl, IS_MOCK } from '@/shared/api/client';
import { primaryPhotoPath, toNumber } from '@/shared/api/mappers';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { Obstruction, RoofAssessment } from './types';

function toObstruction(item: Schemas['ObstructionOut'], index: number): Obstruction {
  return {
    id: String(index),
    obstruction_type: item.obstruction_type,
    bbox_x: toNumber(item.bbox_x) ?? 0,
    bbox_y: toNumber(item.bbox_y) ?? 0,
    bbox_w: toNumber(item.bbox_w) ?? 0,
    bbox_h: toNumber(item.bbox_h) ?? 0,
    severity: item.severity ?? 'medium',
  };
}

/** The assessment arrives inside the request. It is null until the AI job exists. */
export async function getAssessment(requestId: string): Promise<RoofAssessment> {
  if (IS_MOCK) return mock.getAssessment(requestId);
  const request = await apiRequest<Schemas['RequestOut']>(`/requests/${requestId}`);
  const photoPath = primaryPhotoPath(request.attachments);
  const assessment = request.roof_assessment;
  return {
    status: assessment?.status ?? 'failed',
    photo_url: photoPath ? await fetchFileUrl(photoPath) : null,
    usable_area_sqm: toNumber(assessment?.usable_area_sqm),
    max_kw_by_area: toNumber(assessment?.max_kw_by_area),
    shade_risk: assessment?.shade_risk ?? null,
    summary: assessment?.summary ?? null,
    obstructions: assessment?.obstructions.map(toObstruction) ?? [],
  };
}
