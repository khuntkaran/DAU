import { apiRequest, IS_MOCK } from '@/shared/api/client';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { AuthResponse, OtpRequest, OtpVerify } from './types';

/** The API stores numbers as E.164. People type ten digits. */
function toE164(phone: string) {
  return phone.startsWith('+') ? phone : `+91${phone}`;
}

export async function requestOtp(input: OtpRequest): Promise<void> {
  if (IS_MOCK) return mock.requestOtp(input);
  await apiRequest<Schemas['OtpSent']>('/auth/otp', { method: 'POST', body: { phone: toE164(input.phone) } });
}

export async function verifyOtp(input: OtpVerify): Promise<AuthResponse> {
  if (IS_MOCK) return mock.verifyOtp(input);
  const response = await apiRequest<Schemas['TokenResponse']>('/auth/verify', {
    method: 'POST',
    body: { ...input, phone: toE164(input.phone) },
  });
  return {
    token: response.access_token,
    user: { ...response.user, full_name: response.user.full_name ?? response.user.phone },
  };
}
