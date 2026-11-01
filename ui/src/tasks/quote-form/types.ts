import type { QuoteStatus, RequestStatus } from '@/shared/types/common';
import type { LineItemType } from '@/tasks/compare-quotes/types';

export interface QuoteInput {
  system_kw: number;
  price_total_inr: number;
  panel_brand: string;
  panel_wattage: number | null;
  panel_is_dcr: boolean | null;
  inverter_brand: string;
  inverter_kw: number | null;
  warranty_panel_yrs: number;
  warranty_inverter_yrs: number;
  warranty_work_yrs: number;
  timeline_days: number;
  included_items: LineItemType[];
  notes: string;
}

/** What a vendor sees. Exact location and phone appear only after acceptance. */
export interface VendorRequestDetail {
  id: string;
  request_code: string;
  status: RequestStatus;
  approx_lat: number;
  approx_lng: number;
  district: string | null;
  monthly_units: number;
  budget_inr: number;
  roof_area_sqm: number;
  suggested_kw: number;
  my_quote_status: QuoteStatus | null;
  household_phone: string | null;
  exact_location: { lat: number; lng: number } | null;
}
