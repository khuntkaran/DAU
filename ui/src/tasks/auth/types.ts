import type { Session } from '@/shared/api/session';
import type { Role } from '@/shared/types/common';

export interface OtpRequest {
  phone: string;
}

export interface OtpVerify {
  phone: string;
  code: string;
}

export type AuthResponse = Session;

export const DEMO_PHONES: Record<Role, string> = {
  household: '9000000001',
  vendor: '9000000002',
  admin: '9000000003',
};
