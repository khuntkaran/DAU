/**
 * The API has no /admin routes yet, so these always use sample data, and the
 * page says so. When the routes exist, switch back with apiRequest and IS_MOCK.
 */
import * as mock from './mock';
import type { AdminOverview, AdminRequest, AdminVendor, FlaggedQuote, VendorAction } from './types';

export function getOverview(): Promise<AdminOverview> {
  return mock.getOverview();
}

export function listAdminRequests(): Promise<AdminRequest[]> {
  return mock.listAdminRequests();
}

export function cancelRequest(id: string): Promise<void> {
  return mock.cancelRequest(id);
}

export function listAdminVendors(): Promise<AdminVendor[]> {
  return mock.listAdminVendors();
}

export function updateVendor(id: string, action: VendorAction): Promise<void> {
  return mock.updateVendor(id, action);
}

export function listFlaggedQuotes(): Promise<FlaggedQuote[]> {
  return mock.listFlaggedQuotes();
}

export function markQuoteReviewed(quoteId: string): Promise<void> {
  return mock.markQuoteReviewed(quoteId);
}
