import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getState, resetState, saveState } from '@/shared/mock/store';
import { clearPendingOtps, requestOtp, verifyOtp } from './mock';

const phone = '9000000002';

describe('mock OTP', () => {
  beforeEach(() => {
    resetState();
    clearPendingOtps();
    vi.useRealTimers();
  });

  it('refuses a code when none was requested', async () => {
    await expect(verifyOtp({ phone, code: '123456' })).rejects.toMatchObject({ code: 'otp_expired' });
  });

  it('accepts the right code once only', async () => {
    await requestOtp({ phone });
    await expect(verifyOtp({ phone, code: '123456' })).resolves.toMatchObject({ user: { role: 'vendor' } });
    await expect(verifyOtp({ phone, code: '123456' })).rejects.toMatchObject({ code: 'otp_expired' });
  });

  it('locks a code after five wrong attempts', async () => {
    await requestOtp({ phone });
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await expect(verifyOtp({ phone, code: '000000' })).rejects.toMatchObject({ code: 'invalid_code' });
    }
    await expect(verifyOtp({ phone, code: '123456' })).rejects.toMatchObject({ code: 'too_many_attempts' });
  });

  it('expires a code after five minutes', async () => {
    await requestOtp({ phone });
    const now = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(now + 5 * 60 * 1000 + 1);
    await expect(verifyOtp({ phone, code: '123456' })).rejects.toMatchObject({ code: 'otp_expired' });
    vi.restoreAllMocks();
  });

  it('refuses a suspended vendor', async () => {
    const state = getState();
    state.vendors[0]!.verification_status = 'suspended';
    saveState(state);
    await requestOtp({ phone });
    await expect(verifyOtp({ phone, code: '123456' })).rejects.toMatchObject({ code: 'account_suspended' });
  });
});
