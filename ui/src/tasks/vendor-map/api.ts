import { fetchAllPages, IS_MOCK } from '@/shared/api/client';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { BoundingBox, OpenRequest, VendorQuote } from './types';

export async function listMyQuotes(): Promise<VendorQuote[]> {
  if (IS_MOCK) return mock.listMyQuotes();
  const quotes = await fetchAllPages<Schemas['VendorQuoteSummary']>('/quotes/mine');
  return quotes.map(({ contact, submitted_at: _submitted, ...quote }) => ({
    ...quote,
    system_kw: Number(quote.system_kw),
    contact_phone: contact?.phone ?? null,
  }));
}

export async function listOpenRequests(box: BoundingBox): Promise<OpenRequest[]> {
  if (IS_MOCK) return mock.listOpenRequests(box);
  const bbox = [box.west, box.south, box.east, box.north].join(',');
  const [pins, quotes] = await Promise.all([
    fetchAllPages<Schemas['OpenRequestPin']>(`/requests/open?bbox=${encodeURIComponent(bbox)}`),
    listMyQuotes(),
  ]);
  return pins.map((pin) => ({
    id: pin.id,
    request_code: pin.request_code,
    status: pin.quotes_count > 0 ? 'quoted' : 'open',
    approx_lat: pin.approx_lat,
    approx_lng: pin.approx_lng,
    district: pin.district,
    monthly_units: pin.monthly_units,
    budget_inr: pin.budget_inr,
    roof_area_sqm: Number(pin.roof_area_sqm ?? 0),
    suggested_kw: Number(pin.recommended_kw),
    my_quote_status: quotes.find(({ request_id: id }) => id === pin.id)?.status ?? null,
  }));
}
