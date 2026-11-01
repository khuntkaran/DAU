import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { AdminOverview, AdminRequest, AdminVendor, FlaggedQuote, VendorAction } from './types';

export function getOverview(): Promise<AdminOverview> {
  return IS_MOCK ? mock.getOverview() : apiRequest('/admin/overview');
}

export function listAdminRequests(): Promise<AdminRequest[]> {
  return IS_MOCK ? mock.listAdminRequests() : apiRequest('/admin/requests');
}

export function cancelRequest(id: string): Promise<void> {
  return IS_MOCK ? mock.cancelRequest(id) : apiRequest(`/admin/requests/${id}/cancel`, { method: 'POST' });
}

export function listAdminVendors(): Promise<AdminVendor[]> {
  return IS_MOCK ? mock.listAdminVendors() : apiRequest('/admin/vendors');
}

export function updateVendor(id: string, action: VendorAction): Promise<void> {
  return IS_MOCK
    ? mock.updateVendor(id, action)
    : apiRequest(`/admin/vendors/${id}/${action}`, { method: 'POST' });
}

export function listFlaggedQuotes(): Promise<FlaggedQuote[]> {
  return IS_MOCK ? mock.listFlaggedQuotes() : apiRequest('/admin/flagged-quotes');
}

export function markQuoteReviewed(quoteId: string): Promise<void> {
  return IS_MOCK
    ? mock.markQuoteReviewed(quoteId)
    : apiRequest(`/admin/flagged-quotes/${quoteId}/review`, { method: 'POST' });
}
