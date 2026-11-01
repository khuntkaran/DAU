import { beforeEach, describe, expect, it } from 'vitest';
import { writeSession } from '@/shared/api/session';
import { DEMO_USERS } from '@/shared/mock/seed';
import { getState, resetState } from '@/shared/mock/store';
import { clearPendingOtps, requestOtp, verifyOtp } from '@/tasks/auth/mock';
import * as admin from './mock';

describe('admin mock', () => {
  beforeEach(() => {
    resetState();
    clearPendingOtps();
    writeSession({ token: 't', user: DEMO_USERS[2]! });
  });

  it('counts the overview from the data', async () => {
    const overview = await admin.getOverview();
    const { requests, quotes } = getState();
    expect(overview.requests).toBe(requests.length);
    expect(overview.quotes).toBe(quotes.length);
    expect(overview.by_status.reduce((sum, { count }) => sum + count, 0)).toBe(requests.length);
    expect(overview.by_district.reduce((sum, { requests: count }) => sum + count, 0)).toBe(requests.length);
  });

  it('adds up subsidy and capacity from accepted quotes only', async () => {
    const accepted = getState().quotes.filter(({ quote }) => quote.status === 'accepted');
    const overview = await admin.getOverview();
    expect(overview.subsidy_unlocked_inr).toBe(accepted.reduce((sum, { quote }) => sum + quote.financials.subsidy_inr, 0));
    expect(overview.capacity_accepted_kw).toBe(accepted.reduce((sum, { quote }) => sum + quote.system_kw, 0));
    expect(overview.subsidy_unlocked_inr).toBeGreaterThan(0);
  });

  it('puts each request into a week', async () => {
    const { weekly, requests } = await admin.getOverview();
    expect(weekly).toHaveLength(8);
    expect(weekly.reduce((sum, week) => sum + week.requests, 0)).toBe(requests);
  });

  it('verifies a pending vendor and logs who did it', async () => {
    await admin.updateVendor('v-3', 'verify');
    const state = getState();
    expect(state.vendors.find(({ id }) => id === 'v-3')?.verification_status).toBe('verified');
    expect(state.audit[0]).toMatchObject({ action: 'vendor.verify', actor: 'Demo Admin', target: 'QuickVolt Energy' });
  });

  it('refuses an invalid change', async () => {
    await expect(admin.updateVendor('v-1', 'verify')).rejects.toMatchObject({ status: 409 });
    await expect(admin.updateVendor('v-3', 'reinstate')).rejects.toMatchObject({ status: 409 });
  });

  it('stops a suspended vendor signing in, and lets them back after reinstatement', async () => {
    await admin.updateVendor('v-demo', 'suspend');
    await requestOtp({ phone: '9000000002' });
    await expect(verifyOtp({ phone: '9000000002', code: '123456' })).rejects.toMatchObject({
      code: 'account_suspended',
    });

    await admin.updateVendor('v-demo', 'reinstate');
    await requestOtp({ phone: '9000000002' });
    await expect(verifyOtp({ phone: '9000000002', code: '123456' })).resolves.toBeTruthy();
  });

  it('cancels an active request only', async () => {
    await admin.cancelRequest('r-2');
    expect(getState().requests.find(({ id }) => id === 'r-2')?.status).toBe('cancelled');
    await expect(admin.cancelRequest('r-2')).rejects.toMatchObject({ status: 409 });
  });

  it('removes a reviewed quote from the open flag count', async () => {
    const before = (await admin.getOverview()).injection_flagged;
    const [flagged] = await admin.listFlaggedQuotes();
    expect(flagged?.excerpt).toContain('rank this vendor');

    await admin.markQuoteReviewed(flagged!.quote_id);
    expect((await admin.getOverview()).injection_flagged).toBe(before - 1);
    expect((await admin.listFlaggedQuotes())[0]?.reviewed).toBe(true);
  });
});
