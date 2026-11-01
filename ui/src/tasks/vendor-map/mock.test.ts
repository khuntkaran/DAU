import { beforeEach, describe, expect, it } from 'vitest';
import { resetState } from '@/shared/mock/store';
import { listOpenRequests } from './mock';

const GUJARAT = { south: 20, west: 68, north: 25, east: 75 };

describe('vendor open requests', () => {
  beforeEach(() => resetState());

  it('never exposes exact location, phone or household', async () => {
    const [first] = await listOpenRequests(GUJARAT);
    expect(first).toBeDefined();
    expect(Object.keys(first!)).not.toEqual(expect.arrayContaining(['lat']));
    expect(JSON.stringify(first)).not.toMatch(/phone|household/);
  });

  it('rounds location to about 500 m', async () => {
    const results = await listOpenRequests(GUJARAT);
    for (const { approx_lat: lat } of results) {
      expect(Math.abs(lat / 0.005 - Math.round(lat / 0.005))).toBeLessThan(1e-6);
    }
  });

  it('filters by the bounding box', async () => {
    const results = await listOpenRequests({ south: 23.1, west: 72.5, north: 23.3, east: 72.8 });
    expect(results.map(({ request_code: code }) => code)).toEqual(['SR-2026-000002']);
  });
});
