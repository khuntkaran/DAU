import { ApiError } from '@/shared/api/client';
import { DEMO_VENDOR_ID } from '@/shared/mock/seed';
import { delay, getState } from '@/shared/mock/store';
import type { AuthResponse, OtpRequest, OtpVerify } from './types';

export const DEMO_CODE = '123456';
const OTP_LIFETIME_MS = 5 * 60 * 1000;
const MAX_ATTEMPTS = 5;

interface PendingOtp {
  expiresAt: number;
  attempts: number;
}

/** A code exists only after requestOtp, so no one can sign in by skipping that step. */
const pendingOtps = new Map<string, PendingOtp>();

export function clearPendingOtps() {
  pendingOtps.clear();
}

export async function requestOtp({ phone }: OtpRequest): Promise<void> {
  await delay();
  pendingOtps.set(phone, { expiresAt: Date.now() + OTP_LIFETIME_MS, attempts: 0 });
}

export async function verifyOtp({ phone, code }: OtpVerify): Promise<AuthResponse> {
  await delay();
  const pending = pendingOtps.get(phone);
  if (!pending || Date.now() > pending.expiresAt) {
    pendingOtps.delete(phone);
    throw new ApiError(401, 'otp_expired', 'Request a new code.');
  }
  if (pending.attempts >= MAX_ATTEMPTS) {
    pendingOtps.delete(phone);
    throw new ApiError(429, 'too_many_attempts', 'Too many attempts.');
  }
  if (code !== DEMO_CODE) {
    pending.attempts += 1;
    throw new ApiError(401, 'invalid_code', 'That code is not correct.');
  }

  const state = getState();
  const user = state.users.find((item) => item.phone === phone);
  const vendor = state.vendors.find(({ id }) => id === DEMO_VENDOR_ID);
  if (user?.role === 'vendor' && vendor?.verification_status === 'suspended') {
    pendingOtps.delete(phone);
    throw new ApiError(403, 'account_suspended', 'This account is suspended.');
  }

  pendingOtps.delete(phone);
  // Any other number signs in as a new household, as the real OTP flow would.
  return {
    token: `mock-${phone}`,
    user: user ?? {
      id: `u-${phone}`,
      role: 'household',
      full_name: 'New household',
      phone,
      preferred_lang: 'en',
    },
  };
}
