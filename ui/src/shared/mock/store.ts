/** In-browser stand-in for the database, so the demo flow works before the API exists. */
import { ApiError } from '@/shared/api/client';
import type { SolarRequest, User } from '@/shared/types/common';
import type { AuditEntry, VendorStatus } from '@/tasks/admin/types';
import type { Quote } from '@/tasks/compare-quotes/types';
import type { QuoteInput } from '@/tasks/quote-form/types';
import type { RoofAssessment } from '@/tasks/roof-assessment/types';
import { createSeed } from './seed';

export interface StoredQuote {
  quote: Quote;
  input: QuoteInput;
  created_at: string;
  flag_reviewed: boolean;
}

export interface MockVendor {
  id: string;
  name: string;
  phone: string;
  rating: number;
  verified: boolean;
  verification_status: VendorStatus;
  mnre_registration_no: string | null;
  district: string;
  service_radius_km: number;
  installations_completed: number;
}

export interface MockState {
  users: User[];
  vendors: MockVendor[];
  requests: SolarRequest[];
  quotes: StoredQuote[];
  assessments: Record<string, RoofAssessment & { ready_at: number }>;
  audit: AuditEntry[];
}

// Bump this whenever the shape changes, so old browser data is not read as new.
const KEY = 'suryasetu.mock.v2';
let memory: MockState | null = null;

export function getState(): MockState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as MockState;
  } catch {
    // Fall through to the in-memory copy.
  }
  memory ??= createSeed();
  return memory;
}

export function saveState(state: MockState) {
  memory = state;
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Large photos can exceed storage. The state still lives in memory.
  }
}

export function resetState() {
  memory = null;
}

export function nextCode(prefix: string, count: number) {
  return `${prefix}-2026-${String(count + 1).padStart(6, '0')}`;
}

export function notFound(): never {
  throw new ApiError(404, 'not_found', 'Not found.');
}

/** Short wait so loading states appear as they will against the real API. */
export function delay(ms = 150) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
