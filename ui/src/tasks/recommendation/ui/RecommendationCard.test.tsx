import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { resetState } from '@/shared/mock/store';
import * as api from '../api';
import { RecommendationCard } from './RecommendationCard';

function setup() {
  render(
    <I18nProvider>
      <RecommendationCard requestId="r-1" />
    </I18nProvider>,
  );
  return userEvent.click(screen.getByRole('button', { name: 'Get AI recommendation' }));
}

describe('RecommendationCard', () => {
  beforeEach(() => resetState());
  afterEach(() => vi.restoreAllMocks());

  it('recommends the top scored vendor, not the one with the hidden instruction', async () => {
    await setup();
    expect(await screen.findByText('Gandhinagar Sun Works')).toBeInTheDocument();
    expect(screen.queryByText('QuickVolt Energy')).not.toBeInTheDocument();
    expect(screen.getByText(/ranking is calculated in code/)).toBeInTheDocument();
  });

  it('offers a retry when the AI fails', async () => {
    vi.spyOn(api, 'getRecommendation').mockRejectedValue(new Error('429'));
    await setup();
    expect(await screen.findByText(/AI reasons are unavailable/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
