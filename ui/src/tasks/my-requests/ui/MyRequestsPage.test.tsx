import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writeSession } from '@/shared/api/session';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { resetState } from '@/shared/mock/store';
import { DEMO_USERS } from '@/shared/mock/seed';
import * as api from '../api';
import { MyRequestsPage } from './MyRequestsPage';

function setup() {
  render(
    <I18nProvider>
      <MyRequestsPage />
    </I18nProvider>,
  );
}

describe('MyRequestsPage', () => {
  beforeEach(() => {
    resetState();
    vi.restoreAllMocks();
    writeSession({ token: 't', user: DEMO_USERS[0]! });
  });

  it('lists only this household’s requests', async () => {
    setup();
    expect(await screen.findByText('SR-2026-000001')).toBeInTheDocument();
    expect(screen.queryByText('SR-2026-000002')).not.toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    writeSession({ token: 't', user: { ...DEMO_USERS[0]!, id: 'someone-new' } });
    setup();
    expect(await screen.findByText('You have not posted a request yet.')).toBeInTheDocument();
  });

  it('offers a retry on failure', async () => {
    vi.spyOn(api, 'listMyRequests').mockRejectedValue(new Error('down'));
    setup();
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
