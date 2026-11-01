import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { AddressResult, NewRequestInput, NewRequestResponse, UploadedFile } from './types';

const SEARCH_URL = 'https://nominatim.openstreetmap.org/search';

export function uploadFile(file: File): Promise<UploadedFile> {
  if (IS_MOCK) return mock.uploadFile(file);
  const body = new FormData();
  body.append('file', file);
  return apiRequest('/uploads', { method: 'POST', body });
}

export function createRequest(input: NewRequestInput): Promise<NewRequestResponse> {
  return IS_MOCK ? mock.createRequest(input) : apiRequest('/requests', { method: 'POST', body: input });
}

/** Called only when the user presses search, as Nominatim's usage policy requires. */
export async function searchAddress(query: string): Promise<AddressResult[]> {
  const params = new URLSearchParams({ format: 'jsonv2', limit: '5', countrycodes: 'in', q: query });
  const response = await fetch(`${SEARCH_URL}?${params}`);
  if (!response.ok) throw new Error('Address search failed.');
  const places = (await response.json()) as { display_name: string; lat: string; lon: string }[];
  return places.map(({ display_name: label, lat, lon }) => ({ label, lat: Number(lat), lng: Number(lon) }));
}
