import { ApiError } from '@/shared/api/client';
import { buildQuotes, DEMO_VENDOR_ID } from '@/shared/mock/seed';
import { delay, getState, notFound, saveState } from '@/shared/mock/store';
import { toOpenRequest } from '@/tasks/vendor-map/mock';
import type { QuoteInput, VendorRequestDetail } from './types';

export async function getVendorRequest(id: string): Promise<VendorRequestDetail> {
  await delay();
  const state = getState();
  const request = state.requests.find((item) => item.id === id);
  if (!request) notFound();
  const summary = toOpenRequest(request);
  const accepted = summary.my_quote_status === 'accepted';
  const household = state.users.find((user) => user.id === request.household_id);
  return {
    ...summary,
    household_phone: accepted ? (household?.phone ?? null) : null,
    exact_location: accepted ? { lat: request.lat, lng: request.lng } : null,
  };
}

export async function submitQuote(requestId: string, input: QuoteInput): Promise<void> {
  await delay();
  const state = getState();
  const request = state.requests.find(({ id }) => id === requestId);
  if (!request) notFound();
  const others = state.quotes.filter(({ quote }) => quote.request_id === requestId);
  if (others.some(({ quote }) => quote.vendor_id === DEMO_VENDOR_ID)) {
    throw new ApiError(409, 'already_quoted', 'You have already quoted on this request.');
  }

  // Scores compare quotes with each other, so adding one rescores them all.
  const entries = [
    ...others.map(({ quote, input: saved }) => ({ id: quote.id, vendor: quote.vendor_id, input: saved })),
    { id: `q-${state.quotes.length + 1}-${Date.now()}`, vendor: DEMO_VENDOR_ID, input },
  ];
  const rebuilt = buildQuotes(request, entries, state.vendors);
  const rest = state.quotes.filter(({ quote }) => quote.request_id !== requestId);
  state.quotes = [...rest, ...rebuilt];
  request.status = 'quoted';
  request.quote_count = rebuilt.length;
  saveState(state);
}
