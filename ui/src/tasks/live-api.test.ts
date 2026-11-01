/** Checks the requests sent to the real API and how its responses map to the UI. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

type Route = [method: string, path: string, status: number, body: unknown];

const calculation = {
  rule_version: 'v1',
  citations: [],
  id: 'c',
  scope: 'quote_financials',
  system_kw: '3.00',
  recommended_kw: null,
  kw_band_min: null,
  kw_band_max: null,
  roof_cap_kw: '3.00',
  gross_cost_inr: 185000,
  subsidy_inr: 78000,
  net_cost_inr: 107000,
  annual_generation_kwh: 4320,
  monthly_savings_inr: 2145,
  annual_savings_inr: 25740,
  bill_reduction_pct: '100.00',
  payback_years: '4.2',
  savings_25y_inr: null,
  steps: [{ key: 'x', label: 'Saving', formula: 'a × b', value: '25740', unit: 'INR', rule_key: null }],
  engine_version: 'e',
  computed_at: '2026-11-01T00:00:00Z',
};

function quoteOut(id: string, score: string, extra: object = {}) {
  return {
    id,
    quote_code: `Q-${id}`,
    request_id: 'r',
    vendor: { id: `v-${id}`, company_name: `Vendor ${id}`, mnre_registration_no: 'M', avg_rating: '4.60', rating_count: 3, verification_status: 'verified' },
    status: 'submitted',
    system_kw: '3.00',
    price_total_inr: 185000,
    panel_brand: 'Acme',
    panel_wattage: 545,
    dcr_compliant: true,
    panel_performance_warranty_yrs: 25,
    panel_product_warranty_yrs: 12,
    inverter_brand: 'Volt',
    inverter_capacity_kw: '3.00',
    inverter_warranty_yrs: 10,
    workmanship_warranty_yrs: 5,
    timeline_days: 21,
    line_items: [
      { item_type: 'discom_fees', included: true },
      { item_type: 'earthing', included: true },
      { item_type: 'amc', included: false },
    ],
    financials: calculation,
    review: {
      llm_status: 'queued',
      missing_items: [{ item: 'net_metering_fee', severity: 'low', why: 'x' }],
      warnings: ['Panels are not DCR, so this system may not qualify for the subsidy.', 'Something new'],
      injection_detected: false,
      injection_excerpt: null,
      llm_notes: null,
      reviewed_at: '2026-11-01T00:00:00Z',
    },
    score: {
      total_score: score,
      weights: {},
      explanation: [{ criterion: 'warranty', input: 'i', formula: 'f', points: '20.00' }],
    },
    ...extra,
  };
}

function stubApi(routes: Route[]) {
  const calls: { method: string; url: string; body: unknown; headers: Record<string, string> }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const method = init.method ?? 'GET';
      const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body;
      calls.push({ method, url, body, headers: (init.headers ?? {}) as Record<string, string> });
      const route = routes.find(([m, path]) => m === method && url.endsWith(path));
      if (!route) return Response.json({ error: { code: 'not_found', message: url } }, { status: 404 });
      return Response.json(route[3], { status: route[2] });
    }),
  );
  return calls;
}

describe('real API calls', () => {
  beforeEach(() => {
    vi.stubEnv('NEXT_PUBLIC_API_MODE', 'live');
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('signs in with an E.164 phone and maps the token', async () => {
    const calls = stubApi([
      ['POST', '/auth/otp', 200, { expires_in_s: 300 }],
      ['POST', '/auth/verify', 200, { access_token: 'jwt', expires_in_s: 1, user: { id: 'u', role: 'vendor', full_name: null, phone: '+919000000101', preferred_lang: 'en' } }],
    ]);
    const { requestOtp, verifyOtp } = await import('./auth/api');
    await requestOtp({ phone: '9000000101' });
    const session = await verifyOtp({ phone: '9000000101', code: '123456' });

    expect(calls[0]?.body).toEqual({ phone: '+919000000101' });
    expect(calls[1]?.body).toEqual({ phone: '+919000000101', code: '123456' });
    expect(session.token).toBe('jwt');
    expect(session.user.full_name).toBe('+919000000101');
  });

  it('sends the map box as west, south, east, north and merges my quotes', async () => {
    const calls = stubApi([
      ['GET', '/quotes/mine', 200, { items: [{ id: 'q', quote_code: 'Q', request_id: 'r1', request_code: 'SR', status: 'submitted', price_total_inr: 1, system_kw: '3.00', submitted_at: null, contact: null }], next_cursor: null }],
      ['GET', 'bbox=68%2C20%2C75%2C25', 200, { items: [{ id: 'r1', request_code: 'SR', approx_lat: 23, approx_lng: 72, distance_km: '1', district: 'A', monthly_units: 300, budget_inr: 1, recommended_kw: '2.50', roof_area_sqm: '30.00', quotes_count: 1, submitted_at: null }], next_cursor: null }],
    ]);
    const { listOpenRequests } = await import('./vendor-map/api');
    const [pin] = await listOpenRequests({ south: 20, west: 68, north: 25, east: 75 });

    expect(calls.some(({ url }) => url.includes('bbox=68%2C20%2C75%2C25'))).toBe(true);
    expect(pin).toMatchObject({ suggested_kw: 2.5, roof_area_sqm: 30, status: 'quoted', my_quote_status: 'submitted' });
  });

  it('expands tick boxes into the line items the checklist needs', async () => {
    const { toQuoteCreate } = await import('./quote-form/api');
    const body = toQuoteCreate({
      system_kw: 3, price_total_inr: 185000, panel_brand: 'A', panel_wattage: null, panel_is_dcr: true,
      inverter_brand: 'B', inverter_kw: null, warranty_panel_yrs: 25, warranty_inverter_yrs: 0,
      warranty_work_yrs: 5, timeline_days: 20, included_items: ['net_meter', 'earthing'], notes: ' ',
    });
    expect(body.line_items?.map((item) => item.item_type)).toEqual(['net_meter', 'discom_fees', 'earthing', 'lightning_arrester']);
    expect(body).toMatchObject({ dcr_compliant: true, panel_performance_warranty_yrs: 25, inverter_warranty_yrs: null, notes: null });
  });

  it('maps quotes, sorts by score and keeps the accepted vendor phone', async () => {
    stubApi([
      ['GET', '/requests/r/quotes', 200, { rule_version: 'v', citations: [], request_id: 'r', top_quote_id: 'b', quotes: [quoteOut('a', '70.00'), quoteOut('b', '90.00')] }],
      ['POST', '/quotes/b/accept', 200, { request_id: 'r', request_status: 'accepted', accepted_quote_id: 'b', rejected_quote_ids: ['a'], vendor_contact: { company_name: 'B', contact_person: null, contact_phone: '+911', contact_email: null } }],
    ]);
    const { acceptQuote, listQuotes } = await import('./compare-quotes/api');
    const [top, second] = await listQuotes('r');

    expect(top).toMatchObject({ id: 'b', vendor_name: 'Vendor b', vendor_rating: 4.6, warranty_panel_yrs: 25, system_kw: 3 });
    expect(top?.financials).toMatchObject({ net_cost_inr: 107000, annual_saving_inr: 25740, payback_years: 4.2 });
    expect(top?.financials.steps[0]?.value).toBe('₹25740');
    expect(top?.score?.breakdown.warranty).toBe(20);
    expect(top?.review?.warnings).toEqual(['non_dcr_panels', 'Something new']);
    expect(top?.review?.missing_items[0]).toEqual({ item: 'net_metering_fee', severity: 'medium' });
    expect(top?.included_items).toEqual(['net_meter']);
    expect(second?.id).toBe('a');

    await acceptQuote('b');
    expect((await listQuotes('r'))[0]?.vendor_phone).toBe('+911');
  });

  it('ranks from scores and invents no reasons while the AI job is missing', async () => {
    stubApi([
      ['GET', '/requests/r/quotes', 200, { rule_version: 'v', citations: [], request_id: 'r', top_quote_id: 'b', quotes: [quoteOut('a', '70.00'), quoteOut('b', '90.00')] }],
      ['POST', '/requests/r/recommendation', 501, { error: { code: 'not_implemented', message: 'x' } }],
    ]);
    const { getRecommendation } = await import('./recommendation/api');
    const result = await getRecommendation('r');
    expect(result.recommended_quote_id).toBe('b');
    expect(result.reasons).toEqual([]);
  });

  it('reports no AI result rather than making one up', async () => {
    stubApi([['GET', '/requests/r', 200, { attachments: [], roof_assessment: null }]]);
    const { getAssessment } = await import('./roof-assessment/api');
    await expect(getAssessment('r')).resolves.toMatchObject({ status: 'failed', obstructions: [], photo_url: null });
  });

  it('turns the rule list into a lookup by key', async () => {
    stubApi([['GET', '/rules/current', 200, { version: 'v', checked_on: '2026-11-01', citations: [{ key: 'K', title: 't', source: 's', url: null, status: 'assumption' }] }]]);
    const { getCurrentRules } = await import('./rule-sources/api');
    expect((await getCurrentRules()).citations.K?.source).toBe('s');
  });
});
