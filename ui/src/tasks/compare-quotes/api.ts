import { apiRequest, IS_MOCK } from '@/shared/api/client';
import { toCalculation, toNumber } from '@/shared/api/mappers';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { LineItemType, Quote, QuoteReview, QuoteScore, QuoteWarning, ScoreKey } from './types';

const CONTACTS_KEY = 'suryasetu.vendor-contacts';

const SCORE_KEYS: ScoreKey[] = [
  'net_cost_per_kw',
  'warranty',
  'component_quality',
  'completeness',
  'timeline',
  'vendor_rating',
];

/**
 * The API gives the vendor's contact only in the accept response, so it is kept
 * here to survive a reload. It can go once GET /requests/{id}/quotes includes it.
 */
function readContacts(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(CONTACTS_KEY) ?? '{}') as Record<string, string>;
  } catch {
    return {};
  }
}

function rememberContact(quoteId: string, phone: string) {
  try {
    localStorage.setItem(CONTACTS_KEY, JSON.stringify({ ...readContacts(), [quoteId]: phone }));
  } catch {
    // The phone number still shows until the page reloads.
  }
}

/** The API sends warnings as English sentences. Known ones become translated labels. */
function toWarning(text: string): QuoteWarning | string {
  if (/DCR/i.test(text)) return 'non_dcr_panels';
  if (/roof/i.test(text)) return 'exceeds_roof_cap';
  return text;
}

function toReview(review: Schemas['QuoteReviewOut'] | null): QuoteReview | null {
  if (!review) return null;
  return {
    missing_items: review.missing_items.map(({ item, severity }) => ({
      item,
      severity: severity === 'high' ? 'high' : 'medium',
    })),
    warnings: review.warnings.map(toWarning),
    injection_detected: review.injection_detected,
    injection_excerpt: review.injection_excerpt,
    llm_notes: review.llm_notes,
  };
}

function toScore(score: Schemas['QuoteScoreOut'] | null): QuoteScore | null {
  if (!score) return null;
  const points = (key: ScoreKey) =>
    Number(score.explanation.find(({ criterion }) => criterion === key)?.points ?? 0);
  return {
    total_score: Number(score.total_score),
    breakdown: Object.fromEntries(SCORE_KEYS.map((key) => [key, points(key)])) as QuoteScore['breakdown'],
  };
}

function toIncludedItems(items: Schemas['LineItemOut'][]): LineItemType[] {
  const included = new Set(items.filter((item) => item.included).map((item) => item.item_type));
  const result: LineItemType[] = [];
  if (included.has('net_meter') || included.has('discom_fees')) result.push('net_meter');
  if (included.has('mounting_structure')) result.push('mounting_structure');
  if (included.has('earthing') && included.has('lightning_arrester')) result.push('earthing');
  if (included.has('amc')) result.push('amc');
  if (included.has('insurance')) result.push('insurance');
  return result;
}

export function toQuote(quote: Schemas['QuoteOut'], contacts: Record<string, string>): Quote {
  return {
    id: quote.id,
    quote_code: quote.quote_code,
    request_id: quote.request_id,
    vendor_id: quote.vendor.id,
    vendor_name: quote.vendor.company_name,
    vendor_rating: toNumber(quote.vendor.avg_rating) ?? 0,
    vendor_verified: quote.vendor.verification_status === 'verified',
    vendor_phone: contacts[quote.id] ?? null,
    status: quote.status,
    system_kw: Number(quote.system_kw),
    price_total_inr: quote.price_total_inr,
    panel_brand: quote.panel_brand,
    panel_wattage: quote.panel_wattage,
    panel_is_dcr: quote.dcr_compliant,
    inverter_brand: quote.inverter_brand,
    inverter_kw: toNumber(quote.inverter_capacity_kw),
    warranty_panel_yrs: quote.panel_performance_warranty_yrs ?? quote.panel_product_warranty_yrs ?? 0,
    warranty_inverter_yrs: quote.inverter_warranty_yrs ?? 0,
    warranty_work_yrs: quote.workmanship_warranty_yrs ?? 0,
    timeline_days: quote.timeline_days,
    included_items: toIncludedItems(quote.line_items),
    financials: toCalculation(quote.financials),
    review: toReview(quote.review),
    score: toScore(quote.score),
  };
}

export async function listQuotes(requestId: string): Promise<Quote[]> {
  if (IS_MOCK) return mock.listQuotes(requestId);
  const comparison = await apiRequest<Schemas['QuoteComparison']>(`/requests/${requestId}/quotes`);
  const contacts = readContacts();
  return comparison.quotes
    .map((quote) => toQuote(quote, contacts))
    .sort((a, b) => (b.score?.total_score ?? 0) - (a.score?.total_score ?? 0));
}

export async function acceptQuote(quoteId: string): Promise<void> {
  if (IS_MOCK) {
    await mock.acceptQuote(quoteId);
    return;
  }
  const result = await apiRequest<Schemas['AcceptResult']>(`/quotes/${quoteId}/accept`, { method: 'POST' });
  if (result.vendor_contact.contact_phone) rememberContact(quoteId, result.vendor_contact.contact_phone);
}
