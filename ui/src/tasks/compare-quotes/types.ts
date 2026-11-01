import type { Calculation, QuoteStatus } from '@/shared/types/common';

export type LineItemType =
  | 'net_meter'
  | 'mounting_structure'
  | 'earthing'
  | 'amc'
  | 'insurance';

export type ScoreKey =
  | 'net_cost_per_kw'
  | 'warranty'
  | 'component_quality'
  | 'completeness'
  | 'timeline'
  | 'vendor_rating';

export type QuoteWarning = 'non_dcr_panels' | 'exceeds_roof_cap';

export interface MissingItem {
  item: string;
  severity: 'medium' | 'high';
}

/** Missing items and injection checks come from code. llm_notes never holds numbers. */
export interface QuoteReview {
  missing_items: MissingItem[];
  /** Known warnings are keys. Anything new from the API arrives as plain text. */
  warnings: (QuoteWarning | string)[];
  injection_detected: boolean;
  injection_excerpt: string | null;
  llm_notes: string | null;
}

export interface QuoteScore {
  total_score: number;
  breakdown: Record<ScoreKey, number>;
}

/** What a household sees. Vendor notes are untrusted and are not returned. */
export interface Quote {
  id: string;
  quote_code: string;
  request_id: string;
  vendor_id: string;
  vendor_name: string;
  vendor_rating: number;
  vendor_verified: boolean;
  /** Null until this quote is accepted. */
  vendor_phone: string | null;
  status: QuoteStatus;
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
  financials: Calculation;
  /** Null while the AI review job is still running. */
  review: QuoteReview | null;
  score: QuoteScore | null;
}
