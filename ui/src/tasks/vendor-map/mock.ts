import { DEMO_VENDOR_ID } from '@/shared/mock/seed';
import { delay, getState } from '@/shared/mock/store';
import type { SolarRequest } from '@/shared/types/common';
import type { BoundingBox, OpenRequest, VendorQuote } from './types';

/** 0.005 degrees is about 500 m, as the privacy rule requires. */
export function roundLocation(value: number) {
  return Math.round(value / 0.005) * 0.005;
}

export function toOpenRequest(request: SolarRequest): OpenRequest {
  const mine = getState().quotes.find(
    ({ quote }) => quote.request_id === request.id && quote.vendor_id === DEMO_VENDOR_ID,
  );
  return {
    id: request.id,
    request_code: request.request_code,
    status: request.status,
    approx_lat: roundLocation(request.lat),
    approx_lng: roundLocation(request.lng),
    district: request.district,
    monthly_units: request.monthly_units,
    budget_inr: request.budget_inr,
    roof_area_sqm: request.roof_area_sqm,
    suggested_kw: request.estimate.system_kw,
    my_quote_status: mine?.quote.status ?? null,
  };
}

export async function listMyQuotes(): Promise<VendorQuote[]> {
  await delay();
  const { quotes, requests } = getState();
  return quotes
    .filter(({ quote }) => quote.vendor_id === DEMO_VENDOR_ID)
    .map(({ quote }) => ({
      id: quote.id,
      quote_code: quote.quote_code,
      request_id: quote.request_id,
      request_code: requests.find(({ id }) => id === quote.request_id)?.request_code ?? '',
      status: quote.status,
      price_total_inr: quote.price_total_inr,
      system_kw: quote.system_kw,
      contact_phone: null,
    }));
}

export async function listOpenRequests(box: BoundingBox): Promise<OpenRequest[]> {
  await delay();
  return getState()
    .requests.filter(({ status }) => status === 'open' || status === 'quoted')
    .filter(
      ({ lat, lng }) => lat >= box.south && lat <= box.north && lng >= box.west && lng <= box.east,
    )
    .map(toOpenRequest);
}
