import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from '@/shared/i18n/en.json';
import { PATHS, ROLE_HOME, ROLE_NAV } from './paths';

const appDir = join(process.cwd(), 'src', 'app');

describe('paths', () => {
  it('has a Next.js page for every route in work plan task 1.6', () => {
    for (const route of [
      'login',
      'household',
      'household/new',
      'household/requests/[id]',
      'vendor',
      'vendor/requests/[id]',
      'admin',
      'admin/requests',
      'admin/vendors',
      'admin/review',
    ]) {
      expect(existsSync(join(appDir, route, 'page.tsx')), route).toBe(true);
    }
  });

  it('builds links with ids', () => {
    expect(PATHS.household.request('r1')).toBe('/household/requests/r1');
    expect(PATHS.vendor.request('r1')).toBe('/vendor/requests/r1');
  });

  it('sends each role to its own area', () => {
    expect(ROLE_HOME.household).toBe('/household');
    expect(ROLE_HOME.vendor).toBe('/vendor');
    expect(ROLE_HOME.admin).toBe('/admin');
  });

  it('has a translation for every navigation label', () => {
    const labels = Object.values(ROLE_NAV).flat();
    for (const item of labels) {
      expect(en).toHaveProperty([item.labelKey]);
    }
  });
});
