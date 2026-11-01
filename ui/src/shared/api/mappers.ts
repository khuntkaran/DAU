/** Turns API responses into UI types. The API sends decimals as strings. */
import type { Calculation, CalculationStep, SolarRequest } from '@/shared/types/common';
import type { components } from './schema';

export type Schemas = components['schemas'];

export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  return Number(value);
}

function toStep(step: Schemas['CalcStep']): CalculationStep {
  const value = step.unit === 'INR' ? `₹${step.value}` : [step.value, step.unit].filter(Boolean).join(' ');
  return { label: step.label, formula: step.formula, value, rule_key: step.rule_key ?? '' };
}

export function toCalculation(calculation: Schemas['CalculationOut']): Calculation {
  return {
    scope: calculation.scope,
    system_kw: Number(calculation.system_kw),
    kw_band_min: toNumber(calculation.kw_band_min),
    kw_band_max: toNumber(calculation.kw_band_max),
    roof_cap_kw: toNumber(calculation.roof_cap_kw),
    gross_cost_inr: calculation.gross_cost_inr,
    subsidy_inr: calculation.subsidy_inr,
    net_cost_inr: calculation.net_cost_inr,
    annual_generation_kwh: calculation.annual_generation_kwh,
    annual_saving_inr: calculation.annual_savings_inr,
    payback_years: toNumber(calculation.payback_years),
    rule_version: calculation.rule_version,
    steps: calculation.steps.map(toStep),
  };
}

export function primaryPhotoPath(attachments: Schemas['AttachmentOut'][]): string | null {
  const photos = attachments.filter(({ kind }) => kind === 'terrace_photo');
  return (photos.find(({ is_primary: primary }) => primary) ?? photos[0])?.url ?? null;
}

export function toSolarRequest(request: Schemas['RequestOut']): SolarRequest {
  return {
    id: request.id,
    request_code: request.request_code,
    status: request.status,
    lat: request.lat,
    lng: request.lng,
    location_source: request.location_source,
    address_text: request.address_text,
    district: request.district,
    state_category: request.state_category,
    monthly_units: request.monthly_units,
    budget_inr: request.budget_inr,
    roof_area_sqm: Number(request.roof_area_sqm ?? 0),
    photo_url: primaryPhotoPath(request.attachments),
    estimate: toCalculation(request.estimate),
    quote_count: request.quotes_count,
    created_at: request.created_at,
  };
}
