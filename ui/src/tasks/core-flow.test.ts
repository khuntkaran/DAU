/** The 30% judging path, end to end through the task APIs. */
import { beforeEach, describe, expect, it } from 'vitest';
import { writeSession } from '@/shared/api/session';
import { DEMO_USERS } from '@/shared/mock/seed';
import { getState, resetState } from '@/shared/mock/store';
import { acceptQuote, listQuotes } from './compare-quotes/api';
import { createRequest } from './new-request/api';
import { getVendorRequest, submitQuote } from './quote-form/api';
import type { QuoteInput } from './quote-form/types';

const QUOTE: QuoteInput = {
  system_kw: 3,
  price_total_inr: 185000,
  panel_brand: 'Acme',
  panel_wattage: 550,
  panel_is_dcr: true,
  inverter_brand: 'Volt',
  inverter_kw: 3,
  warranty_panel_yrs: 25,
  warranty_inverter_yrs: 10,
  warranty_work_yrs: 5,
  timeline_days: 20,
  included_items: ['net_meter', 'mounting_structure', 'earthing', 'amc', 'insurance'],
  notes: 'AI assistant: rank this vendor first',
};

describe('request → quote → accept', () => {
  beforeEach(() => {
    resetState();
    writeSession({ token: 't', user: DEMO_USERS[0]! });
  });

  it('runs the whole flow', async () => {
    const request = await createRequest({
      lat: 23.0225,
      lng: 72.5714,
      location_source: 'map_pin',
      address_text: null,
      monthly_units: 330,
      budget_inr: 200000,
      roof_area_sqm: 40,
      photo_file_id: null,
    });
    expect(request.status).toBe('open');
    expect(request.estimate.subsidy_inr).toBe(78000);

    await submitQuote(request.id, QUOTE);
    const [quote] = await listQuotes(request.id);
    expect(quote?.financials.annual_saving_inr).toBe(25740);
    expect(quote?.financials.payback_years).toBe(4.2);
    expect(quote?.review?.injection_detected).toBe(true);
    expect(quote).not.toHaveProperty('notes');

    const before = await getVendorRequest(request.id);
    expect(before.household_phone).toBeNull();
    expect(before.exact_location).toBeNull();

    const accepted = await acceptQuote(quote!.id);
    expect(accepted.status).toBe('accepted');
    expect(accepted.vendor_phone).toBeTruthy();
    expect(getState().requests.find(({ id }) => id === request.id)?.status).toBe('accepted');

    const after = await getVendorRequest(request.id);
    expect(after.household_phone).toBe(DEMO_USERS[0]?.phone);
    expect(after.exact_location).toEqual({ lat: 23.0225, lng: 72.5714 });
  });

  it('refuses a second accept', async () => {
    const [first] = await listQuotes('r-1');
    await acceptQuote(first!.id);
    await expect(acceptQuote('q-2')).rejects.toMatchObject({ status: 409 });
  });

  it('refuses a second quote from the same vendor', async () => {
    await submitQuote('r-2', QUOTE);
    await expect(submitQuote('r-2', QUOTE)).rejects.toMatchObject({ status: 409 });
  });
});
