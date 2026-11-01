import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { AuthResponse, OtpRequest, OtpVerify } from './types';

export function requestOtp(input: OtpRequest): Promise<void> {
  return IS_MOCK ? mock.requestOtp(input) : apiRequest('/auth/otp', { method: 'POST', body: input });
}

export function verifyOtp(input: OtpVerify): Promise<AuthResponse> {
  return IS_MOCK ? mock.verifyOtp(input) : apiRequest('/auth/verify', { method: 'POST', body: input });
}
