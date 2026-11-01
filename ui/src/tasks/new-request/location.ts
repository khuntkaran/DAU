import type { LatLng } from './types';

export interface DeviceFix extends LatLng {
  accuracy_m: number;
}

export type LocationFailure = 'unsupported' | 'denied' | 'unavailable';

interface LocateOptions {
  /** Called each time the device gives a more accurate position. */
  onImprove: (fix: DeviceFix) => void;
  timeoutMs?: number;
  goodEnoughM?: number;
}

/**
 * Positions sharpen over a few seconds, and the first one is often a coarse
 * network guess, so this keeps listening and returns the best fix it saw.
 * maximumAge 0 stops the browser reusing an old city-level answer.
 */
export function locateDevice({ onImprove, timeoutMs = 15000, goodEnoughM = 30 }: LocateOptions): Promise<DeviceFix> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('unsupported' satisfies LocationFailure));
      return;
    }

    let best: DeviceFix | null = null;

    function finish() {
      clearTimeout(timer);
      navigator.geolocation.clearWatch(watchId);
      if (best) resolve(best);
      else reject(new Error('unavailable' satisfies LocationFailure));
    }

    const timer = setTimeout(finish, timeoutMs);
    const watchId = navigator.geolocation.watchPosition(
      ({ coords }) => {
        if (best && coords.accuracy >= best.accuracy_m) return;
        best = { lat: coords.latitude, lng: coords.longitude, accuracy_m: Math.round(coords.accuracy) };
        onImprove(best);
        if (best.accuracy_m <= goodEnoughM) finish();
      },
      (failure) => {
        if (failure.code === failure.PERMISSION_DENIED) {
          clearTimeout(timer);
          navigator.geolocation.clearWatch(watchId);
          reject(new Error('denied' satisfies LocationFailure));
        }
        // Other errors can be temporary, so keep waiting until the timeout.
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: timeoutMs },
    );
  });
}
