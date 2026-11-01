import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { resetState } from '@/shared/mock/store';
import { VendorMapPage } from './VendorMapPage';

vi.mock('next/dynamic', () => ({ default: () => () => <div>map</div> }));

describe('VendorMapPage', () => {
  beforeEach(() => resetState());

  it('lists open requests and opens the quote page for the selected one', async () => {
    render(
      <I18nProvider>
        <VendorMapPage />
      </I18nProvider>,
    );
    await userEvent.click(await screen.findByRole('button', { name: /SR-2026-000002/ }));
    expect(screen.getByRole('link', { name: 'Prepare quote' })).toHaveAttribute('href', '/vendor/requests/r-2');
  });
});
