/** Main route file. Every link and redirect in the app comes from here. */
import type { Role } from '@/shared/types/common';

export const PATHS = {
  home: '/',
  login: '/login',
  household: {
    home: '/household',
    newRequest: '/household/new',
    request: (id: string) => `/household/requests/${id}`,
  },
  vendor: {
    home: '/vendor',
    request: (id: string) => `/vendor/requests/${id}`,
  },
  admin: {
    home: '/admin',
    requests: '/admin/requests',
    vendors: '/admin/vendors',
    review: '/admin/review',
  },
} as const;

export const ROLE_HOME: Record<Role, string> = {
  household: PATHS.household.home,
  vendor: PATHS.vendor.home,
  admin: PATHS.admin.home,
};

export type NavIcon = 'requests' | 'new' | 'map' | 'dashboard' | 'vendors' | 'review';

export interface NavItem {
  href: string;
  labelKey: string;
  icon: NavIcon;
}

export const ROLE_NAV: Record<Role, NavItem[]> = {
  household: [
    { href: PATHS.household.home, labelKey: 'nav.myRequests', icon: 'requests' },
    { href: PATHS.household.newRequest, labelKey: 'nav.newRequest', icon: 'new' },
  ],
  vendor: [{ href: PATHS.vendor.home, labelKey: 'nav.openRequests', icon: 'map' }],
  admin: [
    { href: PATHS.admin.home, labelKey: 'nav.overview', icon: 'dashboard' },
    { href: PATHS.admin.requests, labelKey: 'nav.adminRequests', icon: 'requests' },
    { href: PATHS.admin.vendors, labelKey: 'nav.adminVendors', icon: 'vendors' },
    { href: PATHS.admin.review, labelKey: 'nav.adminReview', icon: 'review' },
  ],
};
