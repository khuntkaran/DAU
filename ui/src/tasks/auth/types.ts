import { IS_MOCK } from '@/shared/api/client';
import type { Session } from '@/shared/api/session';
import type { Role } from '@/shared/types/common';

export interface OtpRequest {
  phone: string;
}

export interface OtpVerify {
  phone: string;
  code: string;
  /** Needed the first time a phone number signs in. */
  role?: 'household' | 'vendor';
  full_name?: string;
}

export type AuthResponse = Session;

/** Set NEXT_PUBLIC_DEMO_LOGIN=false once real SMS codes are in use. */
export const SHOW_DEMO_LOGIN = process.env.NEXT_PUBLIC_DEMO_LOGIN !== 'false';

/** These match seed/data on the backend. */
export const DEMO_PHONES: Record<Role, string> = IS_MOCK
  ? { household: '9000000001', vendor: '9000000002', admin: '9000000003' }
  : { household: '9000000001', vendor: '9000000101', admin: '9000000900' };
