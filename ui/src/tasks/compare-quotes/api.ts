import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { Quote } from './types';

export function listQuotes(requestId: string): Promise<Quote[]> {
  return IS_MOCK ? mock.listQuotes(requestId) : apiRequest(`/requests/${requestId}/quotes`);
}

export function acceptQuote(quoteId: string): Promise<Quote> {
  return IS_MOCK ? mock.acceptQuote(quoteId) : apiRequest(`/quotes/${quoteId}/accept`, { method: 'POST' });
}
