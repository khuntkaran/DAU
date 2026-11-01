import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { locateDevice } from './location';

type Success = (position: { coords: { latitude: number; longitude: number; accuracy: number } }) => void;
type Failure = (error: { code: number; PERMISSION_DENIED: number }) => void;

let success: Success;
let failure: Failure;
const watchPosition = vi.fn((...args: [Success, Failure, PositionOptions]) => {
  [success, failure] = args;
  return 7;
});
const clearWatch = vi.fn();

const fix = (accuracy: number, latitude = 23) => ({ coords: { latitude, longitude: 72, accuracy } });

describe('locateDevice', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'geolocation', { value: { watchPosition, clearWatch }, configurable: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('asks for high accuracy and refuses cached positions', () => {
    void locateDevice({ onImprove: vi.fn() }).catch(() => {});
    expect(watchPosition.mock.calls[0]?.[2]).toMatchObject({ enableHighAccuracy: true, maximumAge: 0 });
  });

  it('keeps the most accurate fix and ignores worse ones', async () => {
    const onImprove = vi.fn();
    const located = locateDevice({ onImprove });
    success(fix(5000, 23.1));
    success(fix(300, 23.2));
    success(fix(900, 23.3));
    await vi.advanceTimersByTimeAsync(15000);

    await expect(located).resolves.toEqual({ lat: 23.2, lng: 72, accuracy_m: 300 });
    expect(onImprove).toHaveBeenCalledTimes(2);
  });

  it('stops early once the fix is good enough', async () => {
    const located = locateDevice({ onImprove: vi.fn() });
    success(fix(12));
    await expect(located).resolves.toMatchObject({ accuracy_m: 12 });
    expect(clearWatch).toHaveBeenCalledWith(7);
  });

  it('reports a denied permission', async () => {
    const located = locateDevice({ onImprove: vi.fn() });
    failure({ code: 1, PERMISSION_DENIED: 1 });
    await expect(located).rejects.toThrow('denied');
    expect(clearWatch).toHaveBeenCalledWith(7);
  });

  it('keeps waiting through a temporary error', async () => {
    const located = locateDevice({ onImprove: vi.fn() });
    failure({ code: 2, PERMISSION_DENIED: 1 });
    success(fix(20));
    await expect(located).resolves.toMatchObject({ accuracy_m: 20 });
  });

  it('reports when no position arrives', async () => {
    const located = locateDevice({ onImprove: vi.fn() });
    const outcome = expect(located).rejects.toThrow('unavailable');
    await vi.advanceTimersByTimeAsync(15000);
    await outcome;
  });
});
