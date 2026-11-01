import { apiRequest, IS_MOCK } from '@/shared/api/client';
import type { Schemas } from '@/shared/api/mappers';
import type { LineItemType } from '@/tasks/compare-quotes/types';
import { listMyQuotes } from '@/tasks/vendor-map/api';
import * as mock from './mock';
import type { QuoteInput, VendorRequestDetail } from './types';

/** One tick box in the form can cover two API line items, as the checklist expects. */
const LINE_ITEMS: Record<LineItemType, Schemas['LineItemType'][]> = {
  net_meter: ['net_meter', 'discom_fees'],
  mounting_structure: ['mounting_structure'],
  earthing: ['earthing', 'lightning_arrester'],
  amc: ['amc'],
  insurance: ['insurance'],
};

export function toQuoteCreate(input: QuoteInput): Schemas['QuoteCreate'] {
  return {
    system_kw: input.system_kw,
    price_total_inr: input.price_total_inr,
    gst_included: true,
    panel_brand: input.panel_brand,
    panel_wattage: input.panel_wattage,
    dcr_compliant: input.panel_is_dcr === true,
    panel_performance_warranty_yrs: input.warranty_panel_yrs,
    inverter_brand: input.inverter_brand,
    inverter_capacity_kw: input.inverter_kw,
    inverter_warranty_yrs: input.warranty_inverter_yrs || null,
    workmanship_warranty_yrs: input.warranty_work_yrs || null,
    timeline_days: input.timeline_days,
    line_items: input.included_items.flatMap((item) =>
      LINE_ITEMS[item].map((itemType) => ({ item_type: itemType, included: true })),
    ),
    notes: input.notes.trim() || null,
  };
}

export async function getVendorRequest(id: string): Promise<VendorRequestDetail> {
  if (IS_MOCK) return mock.getVendorRequest(id);
  const [view, quotes] = await Promise.all([
    apiRequest<Schemas['VendorRequestView']>(`/requests/${id}`),
    listMyQuotes(),
  ]);
  const contact = view.contact ?? null;
  return {
    id: view.id,
    request_code: view.request_code,
    status: view.status,
    approx_lat: view.approx_lat,
    approx_lng: view.approx_lng,
    district: view.district,
    monthly_units: view.monthly_units,
    budget_inr: view.budget_inr,
    roof_area_sqm: Number(view.roof_area_sqm ?? 0),
    suggested_kw: Number(view.estimate.system_kw),
    my_quote_status: quotes.find(({ request_id: requestId }) => requestId === id)?.status ?? null,
    household_phone: contact?.phone ?? null,
    exact_location: contact ? { lat: contact.lat, lng: contact.lng } : null,
  };
}

export async function submitQuote(requestId: string, input: QuoteInput): Promise<void> {
  if (IS_MOCK) return mock.submitQuote(requestId, input);
  await apiRequest<Schemas['QuoteCreated']>(`/requests/${requestId}/quotes`, {
    method: 'POST',
    body: toQuoteCreate(input),
  });
}
