import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { resetState } from '@/shared/mock/store';
import * as location from '../location';
import { NewRequestPage } from './NewRequestPage';

vi.mock('next/dynamic', () => ({
  default: () =>
    function FakeMap({ onChange }: { onChange: (point: { lat: number; lng: number }) => void }) {
      return <button onClick={() => onChange({ lat: 23.02, lng: 72.57 })}>pin</button>;
    },
}));

function setup() {
  render(
    <I18nProvider>
      <NewRequestPage />
    </I18nProvider>,
  );
}

async function fill() {
  await userEvent.type(screen.getByLabelText('Monthly electricity use (units)'), '330');
  await userEvent.type(screen.getByLabelText('Budget (₹)'), '200000');
  await userEvent.type(screen.getByLabelText('Roof area (m²)'), '40');
}

const SUBMIT = { name: 'See estimate and post request' };

function deviceReports(lat: number, accuracy: number) {
  vi.spyOn(location, 'locateDevice').mockImplementation(async ({ onImprove }) => {
    const fix = { lat, lng: 72.57, accuracy_m: accuracy };
    act(() => onImprove(fix));
    return fix;
  });
}

describe('NewRequestPage', () => {
  beforeEach(() => resetState());
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('requires a pin and positive numbers', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', SUBMIT));
    expect(screen.getByText('Pin your home on the map.')).toBeInTheDocument();
    expect(screen.getAllByText('Enter a number above zero.')).toHaveLength(3);
  });

  it('clears each error as soon as its field is fixed', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', SUBMIT));

    await userEvent.click(screen.getByRole('button', { name: 'pin' }));
    expect(screen.queryByText('Pin your home on the map.')).not.toBeInTheDocument();
    expect(screen.getByText(/Pinned at/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Monthly electricity use (units)'), '330');
    expect(screen.getAllByText('Enter a number above zero.')).toHaveLength(2);
  });

  it('posts a request and shows the estimate from the API', async () => {
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'pin' }));
    await fill();
    await userEvent.click(screen.getByRole('button', SUBMIT));

    expect(await screen.findByText('Request posted')).toBeInTheDocument();
    expect(screen.getByText('Suggested system').nextSibling).toHaveTextContent('3 kW');
    expect(screen.getByText('Central subsidy').nextSibling).toHaveTextContent('₹78,000');
    expect(screen.getByRole('link', { name: 'Go to my request' })).toBeInTheDocument();
  });

  it('warns when the device position is too vague to find a roof', async () => {
    deviceReports(23.1, 4200);
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Use my location' }));
    expect(await screen.findByText('Accurate to about 4.2 km.')).toBeInTheDocument();
    expect(screen.getByText(/not exact/)).toBeInTheDocument();
  });

  it('shows the fix as accurate when the device reports a precise position', async () => {
    deviceReports(23.0225, 12);
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Use my location' }));

    expect(await screen.findByText(/23.02250, 72.57000 · Accurate to about 12 m/)).toBeInTheDocument();
    expect(screen.queryByText(/not exact/)).not.toBeInTheDocument();
  });

  it('removes the accuracy note once the pin is placed by hand', async () => {
    deviceReports(23.1, 4200);
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Use my location' }));
    await screen.findByText(/not exact/);
    await userEvent.click(screen.getByRole('button', { name: 'pin' }));
    expect(screen.queryByText(/not exact/)).not.toBeInTheDocument();
    expect(screen.getByText(/Pinned at 23.02000, 72.57000$/)).toBeInTheDocument();
  });

  it('explains when location permission is denied', async () => {
    vi.spyOn(location, 'locateDevice').mockRejectedValue(new Error('denied'));
    setup();
    await userEvent.click(screen.getByRole('button', { name: 'Use my location' }));
    expect(await screen.findByText(/Location access is blocked/)).toBeInTheDocument();
  });

  it('finds an address and places the pin there', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Response.json([{ display_name: 'Navrangpura, Ahmedabad', lat: '23.036', lon: '72.564' }])),
    );
    setup();
    await userEvent.type(screen.getByLabelText('Search your area or landmark'), 'Navrangpura');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Navrangpura, Ahmedabad' }));

    expect(screen.getByText(/Pinned at 23.03600, 72.56400/)).toBeInTheDocument();
    expect(screen.getByLabelText('Address or landmark')).toHaveValue('Navrangpura, Ahmedabad');
  });
});
