'use client';

import { Sparkles } from 'lucide-react';
import { useState } from 'react';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { Button, Card } from '@/shared/ui/primitives';
import { getRecommendation } from '../api';
import type { Recommendation } from '../types';

type State =
  | { phase: 'idle' }
  | { phase: 'working' }
  | { phase: 'failed' }
  | { phase: 'done'; result: Recommendation };

export function RecommendationCard({ requestId }: { requestId: string }) {
  const { t } = useI18n();
  const [state, setState] = useState<State>({ phase: 'idle' });

  async function load() {
    setState({ phase: 'working' });
    try {
      setState({ phase: 'done', result: await getRecommendation(requestId) });
    } catch {
      setState({ phase: 'failed' });
    }
  }

  const winner =
    state.phase === 'done'
      ? state.result.ranking.find(({ quote_id: id }) => id === state.result.recommended_quote_id)
      : undefined;

  return (
    <Card className="border-primary/40 bg-primary-soft/40">
      <h3 className="flex items-center gap-2 text-lg font-semibold text-ink">
        <Sparkles aria-hidden className="size-5 text-primary" />
        {t('recommend.title')}
      </h3>
      {state.phase === 'idle' && (
        <Button className="mt-3" onClick={load}>
          {t('recommend.get')}
        </Button>
      )}
      {state.phase === 'working' && (
        <p role="status" className="mt-2 animate-pulse text-muted">
          {t('recommend.working')}
        </p>
      )}
      {state.phase === 'failed' && (
        <div className="mt-2">
          <p className="text-muted">{t('recommend.failed')}</p>
          <Button variant="secondary" className="mt-2" onClick={load}>
            {t('common.retry')}
          </Button>
        </div>
      )}
      {state.phase === 'done' && (
        <>
          <p className="mt-2 text-xl font-bold text-primary-strong">{winner?.vendor_name}</p>
          {state.result.reasons.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-ink">
              {state.result.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-muted">{t('recommend.noReasons')}</p>
          )}
          {state.result.caveats && <p className="mt-2 text-sm text-muted">{state.result.caveats}</p>}
          <p className="mt-3 text-sm text-muted">{t('recommend.ranking')}</p>
        </>
      )}
    </Card>
  );
}
