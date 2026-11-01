import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { getState, resetState } from '@/shared/mock/store';
import { QuoteComparison } from './QuoteComparison';

const onAccepted = vi.fn();

function setup(requestId = 'r-1') {
  render(
    <I18nProvider>
      <QuoteComparison requestId={requestId} onAccepted={onAccepted} />
    </I18nProvider>,
  );
}

// jsdom applies no CSS, so the table and the phone cards both render. Tests use the table.
async function table() {
  return within(await screen.findByRole('table'));
}

describe('QuoteComparison', () => {
  beforeEach(() => {
    resetState();
    onAccepted.mockClear();
  });

  it('compares net cost and payback from the API', async () => {
    setup();
    const view = await table();
    expect(view.getByRole('columnheader', { name: /Gandhinagar Sun Works/ })).toBeInTheDocument();
    expect(view.getByText('₹1,07,000')).toBeInTheDocument();
    expect(view.getByText('4.2 years')).toBeInTheDocument();
  });

  it('warns about the hidden instruction on that quote only', async () => {
    setup();
    await table();
    const warnings = screen.getAllByText(/instructions aimed at the AI/);
    // One in the table, one in the phone card, both for the same quote.
    expect(warnings).toHaveLength(2);
    expect(within(warnings[0]!.closest('th')!).getByText('QuickVolt Energy')).toBeInTheDocument();
  });

  it('does not let the injected quote come first', async () => {
    setup();
    const view = await table();
    const headers = view.getAllByRole('columnheader').map((cell) => cell.textContent);
    expect(headers[0]).toContain('Gandhinagar Sun Works');
    expect(headers.at(-1)).toContain('QuickVolt Energy');
  });

  it('flags missing items', async () => {
    setup();
    const view = await table();
    expect(view.getAllByText('Net meter and DISCOM fees').length).toBeGreaterThan(0);
  });

  it('warns about non-DCR panels and a system bigger than the roof', async () => {
    setup();
    const view = await table();
    expect(view.getByText(/Non-DCR panels/)).toBeInTheDocument();
    expect(view.getByText(/Bigger than the roof allows/)).toBeInTheDocument();
  });

  it('asks for confirmation on the page before accepting', async () => {
    setup();
    const view = await table();
    await userEvent.click(view.getAllByRole('button', { name: 'Accept this quote' })[0]!);
    expect(view.getByText('Accept this quote? Other quotes will be declined.')).toBeInTheDocument();
    await userEvent.click(view.getByRole('button', { name: 'Cancel' }));
    expect(getState().requests[0]?.status).toBe('quoted');
  });

  it('accepts one quote, declines the others and reveals the vendor phone', async () => {
    setup();
    const view = await table();
    await userEvent.click(view.getAllByRole('button', { name: 'Accept this quote' })[0]!);
    await userEvent.click(view.getByRole('button', { name: 'Yes, accept' }));

    await waitFor(() => expect(onAccepted).toHaveBeenCalled());
    expect((await table()).getByText(/Vendor contact: 9000000110/)).toBeInTheDocument();
    const statuses = getState()
      .quotes.filter(({ quote }) => quote.request_id === 'r-1')
      .map(({ quote }) => quote.status)
      .sort();
    expect(statuses).toEqual(['accepted', 'rejected', 'rejected', 'rejected']);
  });

  it('shows an empty state with no quotes', async () => {
    setup('r-2');
    expect(await screen.findByText(/No quotes yet/)).toBeInTheDocument();
  });
});
