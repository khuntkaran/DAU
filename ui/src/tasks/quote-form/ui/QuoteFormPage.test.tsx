import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { getState, resetState } from '@/shared/mock/store';
import { QuoteFormPage } from './QuoteFormPage';

function setup(id = 'r-2') {
  render(
    <I18nProvider>
      <QuoteFormPage id={id} />
    </I18nProvider>,
  );
}

async function fillRequired() {
  await userEvent.type(await screen.findByLabelText('Panel brand'), 'Waaree');
  await userEvent.type(screen.getByLabelText('Inverter brand'), 'Growatt');
  await userEvent.type(screen.getByLabelText('Total price (₹)'), '150000');
  await userEvent.type(screen.getByLabelText('System size (kW)'), '2');
  await userEvent.type(screen.getByLabelText('Panel warranty (years)'), '25');
  await userEvent.type(screen.getByLabelText('Timeline (days)'), '20');
}

describe('QuoteFormPage', () => {
  beforeEach(() => resetState());

  it('requires price, components, warranty and timeline', async () => {
    setup();
    await userEvent.click(await screen.findByRole('button', { name: 'Submit quote' }));
    expect(screen.getAllByText('This is required.')).toHaveLength(6);
    expect(getState().requests[1]?.status).toBe('open');
  });

  it('clears an error when its field is fixed', async () => {
    setup();
    await userEvent.click(await screen.findByRole('button', { name: 'Submit quote' }));
    await userEvent.type(screen.getByLabelText('Panel brand'), 'Waaree');
    expect(screen.getAllByText('This is required.')).toHaveLength(5);
  });

  it('submits a quote and moves the request to quoted', async () => {
    setup();
    await fillRequired();
    await userEvent.click(screen.getByLabelText('Mounting structure'));
    await userEvent.click(screen.getByRole('button', { name: 'Submit quote' }));

    expect(await screen.findByText('Quote submitted')).toBeInTheDocument();
    const state = getState();
    expect(state.requests[1]?.status).toBe('quoted');
    expect(state.quotes.at(-1)?.quote.financials.subsidy_inr).toBe(60000);
  });

  it('does not show the household contact before acceptance', async () => {
    setup();
    await fillRequired();
    await userEvent.click(screen.getByRole('button', { name: 'Submit quote' }));
    await screen.findByText('Quote submitted');
    expect(screen.queryByText(/Household contact/)).not.toBeInTheDocument();
  });
});
