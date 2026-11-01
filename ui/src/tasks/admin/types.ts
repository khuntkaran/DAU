import type { RequestStatus } from '@/shared/types/common';

export type VendorStatus = 'pending' | 'verified' | 'rejected' | 'suspended';

export interface WeeklyCount {
  week_start: string;
  requests: number;
}

export interface StatusCount {
  status: RequestStatus;
  count: number;
}

export interface DistrictCount {
  district: string;
  requests: number;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: string;
  action: 'vendor.verify' | 'vendor.reject' | 'vendor.suspend' | 'vendor.reinstate' | 'request.cancel' | 'quote.review';
  target: string;
}

export interface AdminOverview {
  requests: number;
  active_requests: number;
  quotes: number;
  avg_quotes_per_request: number;
  acceptance_rate_percent: number;
  subsidy_unlocked_inr: number;
  capacity_accepted_kw: number;
  vendors: number;
  vendors_pending: number;
  injection_flagged: number;
  weekly: WeeklyCount[];
  by_status: StatusCount[];
  by_district: DistrictCount[];
  recent_activity: AuditEntry[];
}

export interface AdminRequest {
  id: string;
  request_code: string;
  status: RequestStatus;
  district: string | null;
  monthly_units: number;
  budget_inr: number;
  suggested_kw: number;
  subsidy_inr: number;
  quote_count: number;
  created_at: string;
}

export interface AdminVendor {
  id: string;
  name: string;
  district: string;
  rating: number;
  verification_status: VendorStatus;
  mnre_registration_no: string | null;
  installations_completed: number;
  quotes: number;
  quotes_won: number;
}

export interface FlaggedQuote {
  quote_id: string;
  quote_code: string;
  request_code: string;
  vendor_id: string;
  vendor_name: string;
  vendor_status: VendorStatus;
  excerpt: string;
  score: number | null;
  created_at: string;
  reviewed: boolean;
}

export type VendorAction = 'verify' | 'reject' | 'suspend' | 'reinstate';
