'use client';

import { Star, Trophy } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatInr, formatKw, formatMoney } from '@/shared/lib/format';
import { Button, EmptyState, ErrorState, Loading, StatusBadge } from '@/shared/ui/primitives';
import { RecommendationCard } from '@/tasks/recommendation/ui/RecommendationCard';
import { acceptQuote, listQuotes } from '../api';
import type { Quote, ScoreKey } from '../types';

const KNOWN_WARNINGS = ['non_dcr_panels', 'exceeds_roof_cap'];

const SCORE_KEYS: ScoreKey[] = [
  'net_cost_per_kw',
  'warranty',
  'component_quality',
  'completeness',
  'timeline',
  'vendor_rating',
];

interface Row {
  labelKey: string;
  value: (quote: Quote) => ReactNode;
  /** Numeric field to mark the lowest value in the row as best. */
  lowerIsBetter?: (quote: Quote) => number | null;
}

function useRows(): Row[] {
  const { t } = useI18n();
  return [
    { labelKey: 'compare.price', value: (quote) => formatInr(quote.price_total_inr) },
    { labelKey: 'compare.subsidy', value: (quote) => formatInr(quote.financials.subsidy_inr) },
    {
      labelKey: 'compare.netCost',
      value: (quote) => formatMoney(quote.financials.net_cost_inr),
      lowerIsBetter: (quote) => quote.financials.net_cost_inr,
    },
    {
      labelKey: 'compare.payback',
      value: (quote) =>
        quote.financials.payback_years === null ? '—' : `${quote.financials.payback_years} ${t('common.years')}`,
      lowerIsBetter: (quote) => quote.financials.payback_years,
    },
    { labelKey: 'compare.system', value: (quote) => formatKw(quote.system_kw) },
    {
      labelKey: 'compare.panel',
      value: (quote) =>
        `${quote.panel_brand}${quote.panel_wattage ? ` ${quote.panel_wattage} Wp` : ''} · DCR: ${
          quote.panel_is_dcr === null ? t('common.notStated') : t(quote.panel_is_dcr ? 'common.yes' : 'common.no')
        }`,
    },
    { labelKey: 'compare.inverter', value: (quote) => quote.inverter_brand },
    {
      labelKey: 'compare.warranty',
      value: (quote) =>
        `${quote.warranty_panel_yrs} / ${quote.warranty_inverter_yrs} / ${quote.warranty_work_yrs} ${t('common.years')}`,
    },
    {
      labelKey: 'compare.timeline',
      value: (quote) => `${quote.timeline_days} ${t('common.days')}`,
      lowerIsBetter: (quote) => quote.timeline_days,
    },
  ];
}

function bestValue(row: Row, quotes: Quote[]) {
  if (!row.lowerIsBetter) return null;
  const values = quotes.map(row.lowerIsBetter).filter((value): value is number => value !== null);
  return values.length > 1 ? Math.min(...values) : null;
}

function MissingChips({ quote }: { quote: Quote }) {
  const { t } = useI18n();
  if (!quote.review) return <span className="text-muted">{t('compare.pendingReview')}</span>;
  const { missing_items: missing, warnings } = quote.review;
  if (missing.length === 0 && warnings.length === 0) {
    return <span className="text-muted">{t('compare.none')}</span>;
  }
  return (
    <ul className="flex flex-wrap gap-1">
      {warnings.map((warning) => (
        <li key={warning} className="rounded bg-danger-soft px-1.5 py-0.5 text-xs font-medium text-danger">
          ⚠ {KNOWN_WARNINGS.includes(warning) ? t(`warning.${warning}`) : warning}
        </li>
      ))}
      {missing.map(({ item, severity }) => (
        <li
          key={item}
          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
            severity === 'high' ? 'bg-danger-soft text-danger' : 'bg-sun-soft text-sun-strong'
          }`}
        >
          {t(`missing.${item}`)}
        </li>
      ))}
    </ul>
  );
}

function ScoreDetails({ quote }: { quote: Quote }) {
  const { t } = useI18n();
  if (!quote.score) return <span className="text-muted">{t('compare.pendingReview')}</span>;
  return (
    <details>
      <summary className="cursor-pointer text-lg font-bold text-ink">{quote.score.total_score.toFixed(1)}</summary>
      <dl className="mt-2 space-y-1 text-xs text-muted">
        {SCORE_KEYS.map((key) => (
          <div key={key} className="flex justify-between gap-3">
            <dt>{t(`score.${key}`)}</dt>
            <dd className="font-semibold text-ink">{quote.score?.breakdown[key].toFixed(1)}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

function TopScoreBadge() {
  const { t } = useI18n();
  return (
    <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-primary-soft px-2 py-0.5 text-xs font-semibold text-primary-strong">
      <Trophy aria-hidden className="size-3" />
      {t('compare.top')}
    </span>
  );
}

function InjectionWarning({ quote }: { quote: Quote }) {
  const { t } = useI18n();
  if (!quote.review?.injection_detected) return null;
  return (
    <p role="alert" className="mt-2 rounded-lg bg-danger-soft p-2 text-sm font-medium text-danger">
      ⚠ {t('compare.injection')}
    </p>
  );
}

interface AcceptProps {
  quote: Quote;
  locked: boolean;
  busy: boolean;
  onAccept: (quote: Quote) => void;
}

function AcceptControl({ quote, locked, busy, onAccept }: AcceptProps) {
  const { t } = useI18n();
  const [confirming, setConfirming] = useState(false);

  if (quote.status === 'accepted') {
    return (
      <div className="rounded-lg bg-primary-soft p-2 text-sm text-primary-strong">
        <p className="font-semibold">{t('compare.acceptedNote')}</p>
        {quote.vendor_phone && (
          <p className="mt-1">
            {t('compare.contact')}: {quote.vendor_phone}
          </p>
        )}
      </div>
    );
  }
  if (locked) return <StatusBadge status={quote.status} />;
  if (!confirming) {
    return (
      <Button className="w-full" onClick={() => setConfirming(true)}>
        {t('compare.accept')}
      </Button>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-sm text-ink">{t('compare.confirm')}</p>
      <div className="flex gap-2">
        <Button disabled={busy} onClick={() => onAccept(quote)}>
          {t('compare.confirmYes')}
        </Button>
        <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
          {t('compare.cancel')}
        </Button>
      </div>
    </div>
  );
}

function ValueWithBest({ row, quote, best }: { row: Row; quote: Quote; best: number | null }) {
  const { t } = useI18n();
  const isBest = best !== null && row.lowerIsBetter?.(quote) === best;
  return (
    <>
      {row.value(quote)}
      {isBest && (
        <span className="ml-2 rounded bg-primary-soft px-1.5 py-0.5 text-xs font-semibold text-primary-strong">
          {t('compare.best')}
        </span>
      )}
    </>
  );
}

export function QuoteComparison({ requestId, onAccepted }: { requestId: string; onAccepted: () => void }) {
  const { t } = useI18n();
  const { data: quotes, error, loading, reload } = useAsync(() => listQuotes(requestId), [requestId]);
  const [busy, setBusy] = useState(false);
  const [acceptError, setAcceptError] = useState<string>();
  const rows = useRows();

  async function accept(quote: Quote) {
    setBusy(true);
    setAcceptError(undefined);
    try {
      await acceptQuote(quote.id);
      reload();
      onAccepted();
    } catch (failure) {
      setAcceptError(failure instanceof Error ? failure.message : t('common.error'));
      reload();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;
  if (error || !quotes) return <ErrorState onRetry={reload} />;
  if (quotes.length === 0) return <EmptyState>{t('detail.noQuotes')}</EmptyState>;

  const locked = quotes.some((quote) => quote.status === 'accepted');

  return (
    <div className="space-y-4">
      {acceptError && <ErrorState message={acceptError} />}

      <div className="hidden overflow-x-auto rounded-2xl border border-line bg-surface shadow-card lg:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">{t('detail.quotes')}</caption>
          <thead>
            <tr className="border-b border-line">
              <td />
              {quotes.map((quote, index) => (
                <th key={quote.id} scope="col" className={`min-w-52 p-3 align-top ${index === 0 ? 'bg-primary-soft/40' : ''}`}>
                  {index === 0 && <TopScoreBadge />}
                  <span className="block text-base font-bold text-ink">{quote.vendor_name}</span>
                  <span className="inline-flex items-center gap-1 font-normal text-muted">
                    <Star aria-hidden className="size-3.5 fill-sun text-sun" />
                    {quote.vendor_rating}
                  </span>
                  <InjectionWarning quote={quote} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const best = bestValue(row, quotes);
              return (
                <tr key={row.labelKey} className="border-b border-line">
                  <th scope="row" className="p-3 font-medium text-muted">
                    {t(row.labelKey)}
                  </th>
                  {quotes.map((quote) => (
                    <td key={quote.id} className="p-3 text-ink">
                      <ValueWithBest row={row} quote={quote} best={best} />
                    </td>
                  ))}
                </tr>
              );
            })}
            <tr className="border-b border-line">
              <th scope="row" className="p-3 font-medium text-muted">
                {t('compare.missing')}
              </th>
              {quotes.map((quote) => (
                <td key={quote.id} className="p-3">
                  <MissingChips quote={quote} />
                </td>
              ))}
            </tr>
            <tr className="border-b border-line">
              <th scope="row" className="p-3 align-top font-medium text-muted">
                {t('compare.score')}
              </th>
              {quotes.map((quote) => (
                <td key={quote.id} className="p-3 align-top">
                  <ScoreDetails quote={quote} />
                </td>
              ))}
            </tr>
            <tr>
              <td />
              {quotes.map((quote) => (
                <td key={quote.id} className="p-3 align-top">
                  <AcceptControl quote={quote} locked={locked} busy={busy} onAccept={accept} />
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 lg:hidden">
        {quotes.map((quote, index) => (
          <li key={quote.id} className="rounded-2xl border border-line bg-surface p-4 shadow-card">
            {index === 0 && <TopScoreBadge />}
            <h3 className="text-base font-bold text-ink">{quote.vendor_name}</h3>
            <p className="inline-flex items-center gap-1 text-sm text-muted">
              <Star aria-hidden className="size-3.5 fill-sun text-sun" />
              {quote.vendor_rating}
            </p>
            <InjectionWarning quote={quote} />
            <dl className="mt-3 space-y-2 text-sm">
              {rows.map((row) => (
                <div key={row.labelKey} className="flex justify-between gap-4">
                  <dt className="text-muted">{t(row.labelKey)}</dt>
                  <dd className="text-right text-ink">
                    <ValueWithBest row={row} quote={quote} best={bestValue(row, quotes)} />
                  </dd>
                </div>
              ))}
            </dl>
            <div className="mt-3">
              <p className="mb-1 text-sm text-muted">{t('compare.missing')}</p>
              <MissingChips quote={quote} />
            </div>
            <div className="mt-3">
              <p className="mb-1 text-sm text-muted">{t('compare.score')}</p>
              <ScoreDetails quote={quote} />
            </div>
            <div className="mt-4">
              <AcceptControl quote={quote} locked={locked} busy={busy} onAccept={accept} />
            </div>
          </li>
        ))}
      </ul>

      <RecommendationCard requestId={requestId} />
    </div>
  );
}
