import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { resetState } from '@/shared/mock/store';
import * as api from '../api';
import { AdminPage } from './AdminPage';

function setup() {
  render(
    <I18nProvider>
      <AdminPage />
    </I18nProvider>,
  );
}

describe('AdminPage', () => {
  beforeEach(() => resetState());
  afterEach(() => vi.restoreAllMocks());

  it('shows totals and links to the work that needs attention', async () => {
    setup();
    expect(await screen.findByText('Subsidy unlocked')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /vendors awaiting verification/ })).toHaveAttribute('href', '/admin/vendors');
    expect(screen.getByRole('link', { name: /Quotes flagged for AI instructions/ })).toHaveAttribute('href', '/admin/review');
  });

  it('gives each chart a table for screen readers', async () => {
    setup();
    expect(await screen.findByRole('table', { name: 'Requests by district' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'New requests by week' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Requests by status' })).toBeInTheDocument();
  });

  it('offers a retry when loading fails', async () => {
    vi.spyOn(api, 'getOverview').mockRejectedValue(new Error('down'));
    setup();
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
