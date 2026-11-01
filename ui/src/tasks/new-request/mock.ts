import { readSession } from '@/shared/api/session';
import { estimateRequest } from '@/shared/mock/engine';
import { delay, getState, nextCode, saveState } from '@/shared/mock/store';
import type { SolarRequest } from '@/shared/types/common';
import type { NewRequestInput, UploadedFile } from './types';

const AI_REVIEW_MS = 4000;
const uploads = new Map<string, string>();

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('Could not read the file.'));
    reader.readAsDataURL(file);
  });
}

export async function uploadFile(file: File): Promise<UploadedFile> {
  const url = await readAsDataUrl(file);
  const file_id = `f-${uploads.size + 1}-${Date.now()}`;
  uploads.set(file_id, url);
  return { file_id, url };
}

export async function createRequest(input: NewRequestInput): Promise<SolarRequest> {
  await delay();
  const state = getState();
  const photoUrl = input.photo_file_id ? (uploads.get(input.photo_file_id) ?? null) : null;
  const request: SolarRequest = {
    id: `r-${state.requests.length + 1}-${Date.now()}`,
    request_code: nextCode('SR', state.requests.length),
    household_id: readSession()?.user.id ?? 'u-household',
    status: 'open',
    lat: input.lat,
    lng: input.lng,
    location_source: input.location_source,
    address_text: input.address_text,
    district: null,
    state_category: 'general',
    monthly_units: input.monthly_units,
    budget_inr: input.budget_inr,
    roof_area_sqm: input.roof_area_sqm,
    photo_url: photoUrl,
    estimate: estimateRequest(input.monthly_units, input.roof_area_sqm, 'general'),
    quote_count: 0,
    created_at: new Date().toISOString(),
  };
  state.requests.unshift(request);
  if (photoUrl) {
    // The mock pretends the AI finished a few seconds later, with sample findings.
    state.assessments[request.id] = {
      status: 'pending',
      ready_at: Date.now() + AI_REVIEW_MS,
      photo_url: photoUrl,
      usable_area_sqm: Math.round(input.roof_area_sqm * 0.72 * 10) / 10,
      max_kw_by_area: Math.floor(((input.roof_area_sqm * 0.72) / 10) * 2) / 2,
      shade_risk: 'medium',
      summary: 'Sample result: the mock API does not look at your photo.',
      obstructions: [
        { id: 'o-1', obstruction_type: 'water_tank', bbox_x: 0.1, bbox_y: 0.12, bbox_w: 0.25, bbox_h: 0.28, severity: 'medium' },
        { id: 'o-2', obstruction_type: 'staircase_room', bbox_x: 0.65, bbox_y: 0.55, bbox_w: 0.28, bbox_h: 0.35, severity: 'high' },
      ],
    };
  }
  saveState(state);
  return request;
}
