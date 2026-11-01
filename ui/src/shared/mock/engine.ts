/**
 * Stand-in for the backend while it does not exist. Delete this folder when
 * NEXT_PUBLIC_API_MODE=live is in use. Nothing outside src/shared/mock and the
 * tasks' mock.ts files may import it: the browser never does real calculations.
 * engine.test.ts holds these figures to the golden values in rules/tests.
 */
import type { Calculation, CalculationStep, StateCategory } from '@/shared/types/common';
import type { LineItemType, QuoteReview, QuoteScore, ScoreKey } from '@/tasks/compare-quotes/types';
import type { QuoteInput } from '@/tasks/quote-form/types';

const RULE_VERSION = 'pm_surya_ghar_v2024_03';
const GENERATION_KWH_PER_KW_MONTH = 120;
const ROOF_M2_PER_KW = 10;
const DEFAULT_USABLE_FRACTION = 0.8;
const TARIFF_INR_PER_KWH = 6.5;
const WEIGHTS: Record<ScoreKey, number> = {
  net_cost_per_kw: 30,
  warranty: 20,
  component_quality: 15,
  completeness: 15,
  timeline: 10,
  vendor_rating: 10,
};
const REQUIRED_ITEMS: LineItemType[] = [
  'net_meter',
  'mounting_structure',
  'earthing',
  'amc',
  'insurance',
];
const TOTAL_CHECKS = 4 + REQUIRED_ITEMS.length;
const INJECTION_PATTERN =
  /rank this|ignore (all )?previous|system prompt|recommend this|ai assistant|पहले स्थान|પ્રથમ ક્રમ/i;

function roundToHalf(value: number) {
  return Math.round(value * 2) / 2;
}

function subsidyFor(kw: number, category: StateCategory) {
  const [first, second] = category === 'general' ? [30000, 18000] : [33000, 19800];
  return Math.round(Math.min(kw, 2) * first + Math.min(Math.max(kw - 2, 0), 1) * second);
}

function benchmarkCost(kw: number) {
  return Math.round(Math.min(kw, 2) * 50000 + Math.max(kw - 2, 0) * 45000);
}

function sizeBand(units: number): [number, number] {
  if (units <= 150) return [1, 2];
  if (units <= 300) return [2, 3];
  return [3, 10];
}

function financials(
  scope: Calculation['scope'],
  kw: number,
  gross: number,
  units: number,
  category: StateCategory,
  extraSteps: CalculationStep[],
  roofCap: number | null,
): Calculation {
  const subsidy = subsidyFor(kw, category);
  const netCost = Math.max(gross - subsidy, 0);
  const generation = kw * GENERATION_KWH_PER_KW_MONTH * 12;
  const consumption = units * 12;
  const saving = Math.round(Math.min(generation, consumption) * TARIFF_INR_PER_KWH);
  const payback = saving > 0 ? Math.round((netCost / saving) * 10) / 10 : null;
  const [bandMin, bandMax] = sizeBand(units);
  return {
    scope,
    system_kw: kw,
    kw_band_min: bandMin,
    kw_band_max: bandMax,
    roof_cap_kw: roofCap,
    gross_cost_inr: gross,
    subsidy_inr: subsidy,
    net_cost_inr: netCost,
    annual_generation_kwh: generation,
    annual_saving_inr: saving,
    payback_years: payback,
    rule_version: RULE_VERSION,
    steps: [
      ...extraSteps,
      {
        label: 'Central subsidy',
        formula: 'First 2 kW at the first rate, third kW at the second rate, nothing after 3 kW',
        value: `₹${subsidy}`,
        rule_key: category === 'special' ? 'CFA_SPECIAL' : 'CFA_SLAB_1',
      },
      {
        label: 'Generation a year',
        formula: `${kw} kW × ${GENERATION_KWH_PER_KW_MONTH} kWh × 12 months`,
        value: `${generation} kWh`,
        rule_key: 'GENERATION',
      },
      {
        label: 'Saving a year',
        formula: `Lower of generation and use (${consumption} kWh) × ₹${TARIFF_INR_PER_KWH}`,
        value: `₹${saving}`,
        rule_key: 'TARIFF_DEFAULT',
      },
    ],
  };
}

export function estimateRequest(
  units: number,
  roofAreaSqm: number,
  category: StateCategory,
  usableFraction = DEFAULT_USABLE_FRACTION,
): Calculation {
  const wanted = roundToHalf(units / GENERATION_KWH_PER_KW_MONTH);
  const roofCap = Math.floor(((roofAreaSqm * usableFraction) / ROOF_M2_PER_KW) * 2) / 2;
  const kw = Math.min(wanted, roofCap);
  const gross = benchmarkCost(kw);
  return financials(
    'request_estimate',
    kw,
    gross,
    units,
    category,
    [
      {
        label: 'System size',
        formula: `${units} units ÷ ${GENERATION_KWH_PER_KW_MONTH} kWh per kW, to the nearest 0.5 kW`,
        value: `${wanted} kW`,
        rule_key: 'SIZE_BANDS',
      },
      {
        label: 'Roof limit',
        formula: `${roofAreaSqm} m² × ${usableFraction} usable ÷ ${ROOF_M2_PER_KW} m² per kW`,
        value: `${roofCap} kW`,
        rule_key: 'ROOF_AREA',
      },
      {
        label: 'Benchmark cost',
        formula: '₹50,000 per kW to 2 kW, ₹45,000 per kW after',
        value: `₹${gross}`,
        rule_key: 'BENCHMARK_COST',
      },
    ],
    roofCap,
  );
}

export function quoteFinancials(
  price: number,
  kw: number,
  units: number,
  category: StateCategory,
): Calculation {
  return financials('quote_financials', kw, price, units, category, [], null);
}

export function reviewQuote(
  quote: QuoteInput,
  vendorRegistered: boolean,
  roofCapKw: number | null = null,
): QuoteReview {
  const missing: QuoteReview['missing_items'] = [];
  const warnings: QuoteReview['warnings'] = [];
  if (quote.panel_is_dcr === false) warnings.push('non_dcr_panels');
  if (roofCapKw !== null && quote.system_kw > roofCapKw) warnings.push('exceeds_roof_cap');
  if (quote.panel_is_dcr === null) missing.push({ item: 'dcr_panels', severity: 'high' });
  if (quote.warranty_inverter_yrs <= 0) missing.push({ item: 'inverter_warranty', severity: 'medium' });
  if (quote.warranty_work_yrs <= 0) missing.push({ item: 'workmanship_warranty', severity: 'medium' });
  if (!vendorRegistered) missing.push({ item: 'mnre_vendor_registration', severity: 'high' });
  for (const item of REQUIRED_ITEMS) {
    if (!quote.included_items.includes(item)) missing.push({ item, severity: 'medium' });
  }
  const match = INJECTION_PATTERN.exec(quote.notes);
  return {
    missing_items: missing,
    warnings,
    injection_detected: match !== null,
    injection_excerpt: match ? quote.notes.slice(0, 120) : null,
    llm_notes: null,
  };
}

function ratio(value: number, target: number) {
  return target <= 0 ? 0 : Math.min(value / target, 1);
}

interface ScoreInput {
  quote: QuoteInput;
  net_cost_inr: number;
  vendor_rating: number;
  missing_count: number;
}

/** Takes structured fields only, so vendor notes cannot reach a score. */
export function scoreQuotes(inputs: ScoreInput[]): QuoteScore[] {
  const costs = inputs.map(({ net_cost_inr, quote }) => net_cost_inr / quote.system_kw);
  const bestCost = Math.min(...costs);
  const bestTimeline = Math.min(...inputs.map(({ quote }) => quote.timeline_days));

  return inputs.map(({ quote, vendor_rating, missing_count }, index) => {
    const cost = costs[index] ?? 0;
    const parts = [quote.panel_is_dcr === true, quote.panel_brand !== '', quote.inverter_brand !== ''];
    const fractions: Record<ScoreKey, number> = {
      net_cost_per_kw: cost > 0 ? ratio(bestCost, cost) : 0,
      warranty:
        (ratio(quote.warranty_panel_yrs, 25) +
          ratio(quote.warranty_inverter_yrs, 10) +
          ratio(quote.warranty_work_yrs, 5)) /
        3,
      component_quality: parts.filter(Boolean).length / parts.length,
      completeness: (TOTAL_CHECKS - missing_count) / TOTAL_CHECKS,
      timeline: quote.timeline_days > 0 ? ratio(bestTimeline, quote.timeline_days) : 0,
      vendor_rating: ratio(vendor_rating, 5),
    };
    const entries = (Object.keys(WEIGHTS) as ScoreKey[]).map(
      (key) => [key, Math.round(fractions[key] * WEIGHTS[key] * 100) / 100] as const,
    );
    return {
      total_score: Math.round(entries.reduce((sum, [, points]) => sum + points, 0) * 100) / 100,
      breakdown: Object.fromEntries(entries) as Record<ScoreKey, number>,
    };
  });
}
