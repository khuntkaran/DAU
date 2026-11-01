import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import type { RuleCitation } from '../types';
import { RuleSource } from './RuleSource';

function setup(citation: RuleCitation | undefined) {
  return render(
    <I18nProvider>
      <RuleSource citation={citation} />
    </I18nProvider>,
  );
}

describe('RuleSource', () => {
  it('links to a confirmed source with no estimate label', () => {
    setup({ title: 'T', source: 'PIB', url: 'https://example.gov.in', status: 'confirmed' });
    expect(screen.getByRole('link', { name: 'Source: PIB' })).toHaveAttribute('href', 'https://example.gov.in');
    expect(screen.queryByText('Estimate')).not.toBeInTheDocument();
  });

  it('labels an assumption as an estimate and shows no link', () => {
    setup({ title: 'T', source: 'SuryaSetu assumption', url: null, status: 'assumption' });
    expect(screen.getByText('Estimate')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('labels an unverified rule as an estimate', () => {
    setup({ title: 'T', source: 'News', url: 'https://example.com', status: 'verify' });
    expect(screen.getByText('Estimate')).toBeInTheDocument();
  });

  it('renders nothing for an unknown rule', () => {
    const { container } = setup(undefined);
    expect(container).toBeEmptyDOMElement();
  });
});
