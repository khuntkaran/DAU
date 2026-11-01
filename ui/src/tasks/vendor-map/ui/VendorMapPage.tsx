'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useState } from 'react';
import { PATHS } from '@/routes/paths';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatInr, formatKw, joinParts } from '@/shared/lib/format';
import { Card, EmptyState, ErrorState, Loading, PageTitle, Stat, StatusBadge, buttonStyles } from '@/shared/ui/primitives';
import { listOpenRequests } from '../api';
import type { BoundingBox } from '../types';
import { MyQuotes } from './MyQuotes';

const RequestsMap = dynamic(() => import('./RequestsMap'), { ssr: false, loading: () => <Loading /> });

const GUJARAT: BoundingBox = { south: 20, west: 68, north: 25, east: 75 };

export function VendorMapPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(() => listOpenRequests(GUJARAT), []);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = data?.find(({ id }) => id === selectedId);

  return (
    <>
      <PageTitle intro={t('vendor.approx')}>{t('vendor.title')}</PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {data?.length === 0 && <EmptyState>{t('vendor.empty')}</EmptyState>}
      {data && data.length > 0 && (
        <div className="mb-6 grid gap-4 lg:grid-cols-[2fr_1fr]">
          <Card className="p-2 sm:p-2">
            <RequestsMap requests={data} selectedId={selectedId} onSelect={setSelectedId} />
          </Card>
          <div className="space-y-3">
            {selected ? (
              <Card>
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-bold text-ink">{selected.request_code}</h2>
                  <StatusBadge status={selected.status} />
                </div>
                <p className="text-sm text-muted">{selected.district}</p>
                <dl className="mt-3 grid grid-cols-2 gap-3">
                  <Stat label={t('request.units')} value={selected.monthly_units} />
                  <Stat label={t('request.budget')} value={formatInr(selected.budget_inr)} />
                  <Stat label={t('request.roof')} value={selected.roof_area_sqm} />
                  <Stat label={t('vendor.suggested')} value={formatKw(selected.suggested_kw)} />
                </dl>
                <Link
                  href={PATHS.vendor.request(selected.id)}
                  className={`mt-4 w-full ${buttonStyles('primary')}`}
                >
                  {t(selected.my_quote_status ? 'vendor.viewQuote' : 'vendor.quote')}
                </Link>
              </Card>
            ) : (
              <EmptyState>{t('vendor.select')}</EmptyState>
            )}
            {/* The list gives keyboard and screen reader users a way past the map. */}
            <ul aria-label={t('vendor.title')} className="space-y-2">
              {data.map((request) => (
                <li key={request.id}>
                  <button
                    onClick={() => setSelectedId(request.id)}
                    aria-pressed={request.id === selectedId}
                    className="w-full rounded-xl border border-line bg-surface p-3 text-left text-sm shadow-card transition hover:border-primary aria-pressed:border-primary aria-pressed:bg-primary-soft/40"
                  >
                    <span className="font-semibold text-ink">{request.request_code}</span>
                    <span className="block text-muted">
                      {joinParts([request.district, formatKw(request.suggested_kw)])}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      <MyQuotes />
    </>
  );
}
