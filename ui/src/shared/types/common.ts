/** Types used by more than one task. Status values follow db-schema.html. */

export type Role = 'household' | 'vendor' | 'admin';
export type Lang = 'en' | 'hi' | 'gu';
export type StateCategory = 'general' | 'special';

export type RequestStatus =
  | 'draft'
  | 'open'
  | 'quoted'
  | 'accepted'
  | 'completed'
  | 'cancelled'
  | 'expired';

export type QuoteStatus =
  | 'draft'
  | 'submitted'
  | 'revised'
  | 'accepted'
  | 'rejected'
  | 'withdrawn'
  | 'expired';

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export interface User {
  id: string;
  role: Role;
  full_name: string;
  phone: string;
  preferred_lang: Lang;
}

/** One line of working shown to the user. rule_key links to a source. */
export interface CalculationStep {
  label: string;
  formula: string;
  value: string;
  rule_key: string;
}

/** Every number here is calculated by the backend rules engine, never by the LLM. */
export interface Calculation {
  scope: 'request_estimate' | 'quote_financials';
  system_kw: number;
  kw_band_min: number | null;
  kw_band_max: number | null;
  roof_cap_kw: number | null;
  gross_cost_inr: number;
  subsidy_inr: number;
  net_cost_inr: number;
  annual_generation_kwh: number;
  annual_saving_inr: number;
  payback_years: number | null;
  rule_version: string;
  steps: CalculationStep[];
}

export interface SolarRequest {
  id: string;
  request_code: string;
  household_id: string;
  status: RequestStatus;
  lat: number;
  lng: number;
  location_source: 'map_pin' | 'gps' | 'search';
  address_text: string | null;
  district: string | null;
  state_category: StateCategory;
  monthly_units: number;
  budget_inr: number;
  roof_area_sqm: number;
  photo_url: string | null;
  estimate: Calculation;
  quote_count: number;
  created_at: string;
}
