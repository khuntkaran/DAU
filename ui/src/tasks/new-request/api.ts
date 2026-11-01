import { apiRequest, IS_MOCK } from '@/shared/api/client';
import { toSolarRequest } from '@/shared/api/mappers';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { AddressResult, NewRequestInput, NewRequestResponse, UploadedFile } from './types';

const SEARCH_URL = 'https://nominatim.openstreetmap.org/search';

export async function uploadFile(file: File): Promise<UploadedFile> {
  if (IS_MOCK) return mock.uploadFile(file);
  const body = new FormData();
  body.append('file', file);
  body.append('purpose', 'terrace_photo');
  const uploaded = await apiRequest<Schemas['FileOut']>('/uploads', { method: 'POST', body });
  return { file_id: uploaded.id, url: uploaded.url };
}

export async function createRequest(input: NewRequestInput): Promise<NewRequestResponse> {
  if (IS_MOCK) return mock.createRequest(input);
  const { photo_file_id: photo, ...fields } = input;
  const created = await apiRequest<Schemas['RequestOut']>('/requests', {
    method: 'POST',
    body: { ...fields, photo_file_ids: photo ? [photo] : [] },
  });
  return toSolarRequest(created);
}

/** Called only when the user presses search, as Nominatim's usage policy requires. */
export async function searchAddress(query: string): Promise<AddressResult[]> {
  const params = new URLSearchParams({ format: 'jsonv2', limit: '5', countrycodes: 'in', q: query });
  const response = await fetch(`${SEARCH_URL}?${params}`);
  if (!response.ok) throw new Error('Address search failed.');
  const places = (await response.json()) as { display_name: string; lat: string; lon: string }[];
  return places.map(({ display_name: label, lat, lon }) => ({ label, lat: Number(lat), lng: Number(lon) }));
}
