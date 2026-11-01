import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { QuoteInput, VendorRequestDetail } from './types';

export function getVendorRequest(id: string): Promise<VendorRequestDetail> {
  return IS_MOCK ? mock.getVendorRequest(id) : apiRequest(`/vendor/requests/${id}`);
}

export function submitQuote(requestId: string, input: QuoteInput): Promise<void> {
  return IS_MOCK
    ? mock.submitQuote(requestId, input)
    : apiRequest(`/requests/${requestId}/quotes`, { method: 'POST', body: input });
}
