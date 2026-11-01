import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import * as api from '../api';
import type { RoofAssessment } from '../types';
import { RoofAssessmentPanel } from './RoofAssessmentPanel';

const DONE: RoofAssessment = {
  status: 'done',
  photo_url: 'data:image/png;base64,AA==',
  usable_area_sqm: 30.4,
  max_kw_by_area: 3,
  shade_risk: 'medium',
  summary: 'A water tank takes up part of the roof.',
  obstructions: [
    { id: 'o', obstruction_type: 'water_tank', bbox_x: 0.1, bbox_y: 0.2, bbox_w: 0.3, bbox_h: 0.4, severity: 'high' },
  ],
};

function setup() {
  render(
    <I18nProvider>
      <RoofAssessmentPanel requestId="r" />
    </I18nProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('RoofAssessmentPanel', () => {
  it('draws boxes at the positions the assessment gives', async () => {
    vi.spyOn(api, 'getAssessment').mockResolvedValue(DONE);
    setup();
    const label = await screen.findAllByText('Water tank');
    expect(label[0]?.parentElement).toHaveStyle({ left: '10%', top: '20%', width: '30%', height: '40%' });
    expect(screen.getByText('3 kW')).toBeInTheDocument();
  });

  it('shows a pending state while the AI works', async () => {
    vi.spyOn(api, 'getAssessment').mockResolvedValue({ ...DONE, status: 'pending' });
    setup();
    expect(await screen.findByText(/AI review in progress/)).toBeInTheDocument();
  });

  it('keeps the page usable when the AI fails', async () => {
    vi.spyOn(api, 'getAssessment').mockRejectedValue(new Error('429'));
    setup();
    expect(await screen.findByText(/AI review is unavailable/)).toBeInTheDocument();
  });
});
