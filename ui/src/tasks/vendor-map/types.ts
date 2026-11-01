import type { QuoteStatus, RequestStatus } from '@/shared/types/common';

export interface BoundingBox {
  south: number;
  west: number;
  north: number;
  east: number;
}

/** No phone or exact location: vendors get these only after acceptance. */
export interface OpenRequest {
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
}

/** A quote this vendor sent. The phone appears once the household accepts it. */
export interface VendorQuote {
  id: string;
  quote_code: string;
  request_id: string;
  request_code: string;
  status: QuoteStatus;
  price_total_inr: number;
  system_kw: number;
  contact_phone: string | null;
}
