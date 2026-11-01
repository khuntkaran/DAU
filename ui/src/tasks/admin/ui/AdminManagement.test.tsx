import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { getState, resetState } from '@/shared/mock/store';
import { AdminRequestsPage } from './AdminRequestsPage';
import { AdminReviewPage } from './AdminReviewPage';
import { AdminVendorsPage } from './AdminVendorsPage';

function renderPage(page: React.ReactNode) {
  render(<I18nProvider>{page}</I18nProvider>);
}

describe('admin management pages', () => {
  beforeEach(() => resetState());

  it('filters requests by search and status', async () => {
    renderPage(<AdminRequestsPage />);
    await screen.findByText('SR-2026-000002');
    await userEvent.type(screen.getByLabelText('Search by code or district'), 'surat');
    expect(screen.queryByText('SR-2026-000002')).not.toBeInTheDocument();
    expect(screen.getByText('SR-2026-000004')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Filter by status'), 'cancelled');
    expect(screen.queryByText('SR-2026-000004')).not.toBeInTheDocument();
    expect(screen.getByText('SR-2026-000009')).toBeInTheDocument();
  });

  it('shows an empty state when nothing matches', async () => {
    renderPage(<AdminRequestsPage />);
    await screen.findByText('SR-2026-000002');
    await userEvent.type(screen.getByLabelText('Search by code or district'), 'zzz');
    expect(screen.getByText('Nothing matches your filters.')).toBeInTheDocument();
  });

  it('cancels a request only after confirmation', async () => {
    renderPage(<AdminRequestsPage />);
    const row = (await screen.findByText('SR-2026-000002')).closest('tr')!;
    await userEvent.click(within(row).getByRole('button', { name: 'Cancel request' }));
    expect(getState().requests[1]?.status).toBe('open');

    await userEvent.click(within(row).getByRole('button', { name: 'Yes, cancel it' }));
    expect(await within(row).findByText('Cancelled')).toBeInTheDocument();
    expect(getState().requests[1]?.status).toBe('cancelled');
  });

  it('verifies a pending vendor after confirmation', async () => {
    renderPage(<AdminVendorsPage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Verify QuickVolt Energy' }));
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Verify' }));

    const row = (await screen.findByText('QuickVolt Energy')).closest('tr')!;
    expect(await within(row).findByText('Verified')).toBeInTheDocument();
    expect(getState().vendors.find(({ id }) => id === 'v-3')?.verified).toBe(true);
  });

  it('offers only the actions that fit each vendor', async () => {
    renderPage(<AdminVendorsPage />);
    await screen.findByText('QuickVolt Energy');
    expect(screen.getByRole('button', { name: 'Reinstate Girnar Energy Works' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Verify Girnar Energy Works' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Suspend Gandhinagar Sun Works' })).toBeInTheDocument();
  });

  it('shows the flagged text and marks it reviewed', async () => {
    renderPage(<AdminReviewPage />);
    expect(await screen.findByText(/rank this vendor first/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Mark as reviewed' }));
    expect(await screen.findByText('Reviewed')).toBeInTheDocument();
  });
});
