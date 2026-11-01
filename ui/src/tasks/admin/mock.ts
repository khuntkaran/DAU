import { ApiError } from '@/shared/api/client';
import { readSession } from '@/shared/api/session';
import { delay, getState, notFound, saveState } from '@/shared/mock/store';
import type { MockState } from '@/shared/mock/store';
import type { RequestStatus } from '@/shared/types/common';
import type {
  AdminOverview,
  AdminRequest,
  AdminVendor,
  AuditEntry,
  FlaggedQuote,
  VendorAction,
  VendorStatus,
} from './types';

const WEEKS = 8;
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
const STATUS_ORDER: RequestStatus[] = ['open', 'quoted', 'accepted', 'completed', 'cancelled', 'expired'];
const ACTIVE: RequestStatus[] = ['open', 'quoted'];
const DECIDED: RequestStatus[] = ['accepted', 'completed'];

/** The states a vendor may move between, so a stale page cannot make a wrong change. */
const TRANSITIONS: Record<VendorAction, { from: VendorStatus[]; to: VendorStatus }> = {
  verify: { from: ['pending'], to: 'verified' },
  reject: { from: ['pending'], to: 'rejected' },
  suspend: { from: ['verified'], to: 'suspended' },
  reinstate: { from: ['suspended'], to: 'verified' },
};

function audit(state: MockState, action: AuditEntry['action'], target: string) {
  state.audit.unshift({
    id: `a-${state.audit.length + 1}-${Date.now()}`,
    at: new Date().toISOString(),
    actor: readSession()?.user.full_name ?? 'Admin',
    action,
    target,
  });
}

function weeklyCounts(state: MockState) {
  const now = Date.now();
  return Array.from({ length: WEEKS }, (_, index) => {
    const end = now - (WEEKS - 1 - index) * WEEK_MS;
    const start = end - WEEK_MS;
    return {
      week_start: new Date(start).toISOString(),
      requests: state.requests.filter(({ created_at: at }) => {
        const time = Date.parse(at);
        return time > start && time <= end;
      }).length,
    };
  });
}

function districtCounts(state: MockState) {
  const counts = new Map<string, number>();
  for (const { district } of state.requests) {
    const name = district ?? 'Unknown';
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  return [...counts]
    .map(([district, requests]) => ({ district, requests }))
    .sort((a, b) => b.requests - a.requests || a.district.localeCompare(b.district));
}

export async function getOverview(): Promise<AdminOverview> {
  await delay();
  const state = getState();
  const { requests, quotes, vendors } = state;
  const decided = requests.filter(({ status }) => DECIDED.includes(status));
  const decidable = requests.filter(({ status }) => status !== 'open' && status !== 'quoted');
  const accepted = quotes.filter(({ quote }) => quote.status === 'accepted');

  return {
    requests: requests.length,
    active_requests: requests.filter(({ status }) => ACTIVE.includes(status)).length,
    quotes: quotes.length,
    avg_quotes_per_request: requests.length ? Math.round((quotes.length / requests.length) * 10) / 10 : 0,
    acceptance_rate_percent: decidable.length ? Math.round((decided.length / decidable.length) * 100) : 0,
    subsidy_unlocked_inr: accepted.reduce((sum, { quote }) => sum + quote.financials.subsidy_inr, 0),
    capacity_accepted_kw: accepted.reduce((sum, { quote }) => sum + quote.system_kw, 0),
    vendors: vendors.length,
    vendors_pending: vendors.filter(({ verification_status: status }) => status === 'pending').length,
    injection_flagged: quotes.filter(({ quote, flag_reviewed: done }) => quote.review?.injection_detected && !done).length,
    weekly: weeklyCounts(state),
    by_status: STATUS_ORDER.map((status) => ({
      status,
      count: requests.filter((request) => request.status === status).length,
    })),
    by_district: districtCounts(state),
    recent_activity: state.audit.slice(0, 6),
  };
}

export async function listAdminRequests(): Promise<AdminRequest[]> {
  await delay();
  return [...getState().requests]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .map((request) => ({
      id: request.id,
      request_code: request.request_code,
      status: request.status,
      district: request.district,
      monthly_units: request.monthly_units,
      budget_inr: request.budget_inr,
      suggested_kw: request.estimate.system_kw,
      subsidy_inr: request.estimate.subsidy_inr,
      quote_count: request.quote_count,
      created_at: request.created_at,
    }));
}

export async function cancelRequest(id: string): Promise<void> {
  await delay();
  const state = getState();
  const request = state.requests.find((item) => item.id === id);
  if (!request) notFound();
  if (!ACTIVE.includes(request.status)) {
    throw new ApiError(409, 'not_active', 'Only an open request can be cancelled.');
  }
  request.status = 'cancelled';
  audit(state, 'request.cancel', request.request_code);
  saveState(state);
}

export async function listAdminVendors(): Promise<AdminVendor[]> {
  await delay();
  const { vendors, quotes } = getState();
  return vendors.map((vendor) => {
    const own = quotes.filter(({ quote }) => quote.vendor_id === vendor.id);
    return {
      id: vendor.id,
      name: vendor.name,
      district: vendor.district,
      rating: vendor.rating,
      verification_status: vendor.verification_status,
      mnre_registration_no: vendor.mnre_registration_no,
      installations_completed: vendor.installations_completed,
      quotes: own.length,
      quotes_won: own.filter(({ quote }) => quote.status === 'accepted').length,
    };
  });
}

export async function updateVendor(id: string, action: VendorAction): Promise<void> {
  await delay();
  const state = getState();
  const vendor = state.vendors.find((item) => item.id === id);
  if (!vendor) notFound();
  const { from, to } = TRANSITIONS[action];
  if (!from.includes(vendor.verification_status)) {
    throw new ApiError(409, 'invalid_transition', 'This vendor has already changed.');
  }
  vendor.verification_status = to;
  vendor.verified = to === 'verified';
  if (to === 'verified') vendor.mnre_registration_no ??= `MNRE-GJ-${id.slice(2).toUpperCase().padStart(4, '0')}`;
  audit(state, `vendor.${action}`, vendor.name);
  saveState(state);
}

export async function listFlaggedQuotes(): Promise<FlaggedQuote[]> {
  await delay();
  const { quotes, requests, vendors } = getState();
  return quotes
    .filter(({ quote }) => quote.review?.injection_detected)
    .map(({ quote, created_at: createdAt, flag_reviewed: reviewed }) => ({
      quote_id: quote.id,
      quote_code: quote.quote_code,
      request_code: requests.find(({ id }) => id === quote.request_id)?.request_code ?? quote.request_id,
      vendor_id: quote.vendor_id,
      vendor_name: quote.vendor_name,
      vendor_status: vendors.find(({ id }) => id === quote.vendor_id)?.verification_status ?? 'pending',
      excerpt: quote.review?.injection_excerpt ?? '',
      score: quote.score?.total_score ?? null,
      created_at: createdAt,
      reviewed,
    }));
}

export async function markQuoteReviewed(quoteId: string): Promise<void> {
  await delay();
  const state = getState();
  const stored = state.quotes.find(({ quote }) => quote.id === quoteId);
  if (!stored) notFound();
  stored.flag_reviewed = true;
  audit(state, 'quote.review', stored.quote.quote_code);
  saveState(state);
}
