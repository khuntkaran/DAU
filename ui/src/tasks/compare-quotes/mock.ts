import { ApiError } from '@/shared/api/client';
import { delay, getState, notFound, saveState } from '@/shared/mock/store';
import type { Quote } from './types';

export async function listQuotes(requestId: string): Promise<Quote[]> {
  await delay();
  return getState()
    .quotes.map(({ quote }) => quote)
    .filter((quote) => quote.request_id === requestId)
    .sort((a, b) => (b.score?.total_score ?? 0) - (a.score?.total_score ?? 0));
}

export async function acceptQuote(quoteId: string): Promise<Quote> {
  await delay();
  const state = getState();
  const chosen = state.quotes.find(({ quote }) => quote.id === quoteId)?.quote;
  if (!chosen) notFound();
  const request = state.requests.find(({ id }) => id === chosen.request_id);
  if (!request) notFound();
  if (request.status === 'accepted') {
    throw new ApiError(409, 'already_accepted', 'A quote was already accepted.');
  }
  for (const { quote } of state.quotes) {
    if (quote.request_id === chosen.request_id) {
      quote.status = quote.id === quoteId ? 'accepted' : 'rejected';
    }
  }
  chosen.vendor_phone = state.vendors.find(({ id }) => id === chosen.vendor_id)?.phone ?? null;
  request.status = 'accepted';
  saveState(state);
  return chosen;
}
