'use client';

import { ChevronRight, ClipboardList, MessageSquareQuote, Plus, Zap } from 'lucide-react';
import Link from 'next/link';
import { PATHS } from '@/routes/paths';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatKw, joinParts } from '@/shared/lib/format';
import { EmptyState, ErrorState, Loading, PageTitle, StatCard, StatusBadge, buttonStyles } from '@/shared/ui/primitives';
import { listMyRequests } from '../api';

export function MyRequestsPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(listMyRequests, []);
  const quotes = data?.reduce((sum, request) => sum + request.quotes_count, 0) ?? 0;
  const capacity = data?.reduce((sum, request) => sum + request.system_kw, 0) ?? 0;

  return (
    <>
      <PageTitle
        intro={t('mine.intro')}
        actions={
          <Link href={PATHS.household.newRequest} className={buttonStyles('primary')}>
            <Plus aria-hidden className="size-4" />
            {t('nav.newRequest')}
          </Link>
        }
      >
        {t('mine.title')}
      </PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {data?.length === 0 && <EmptyState>{t('mine.empty')}</EmptyState>}
      {data && data.length > 0 && (
        <dl className="mb-6 grid gap-4 sm:grid-cols-3">
          <StatCard icon={ClipboardList} label={t('mine.statRequests')} value={data.length} />
          <StatCard icon={MessageSquareQuote} label={t('mine.statQuotes')} value={quotes} />
          <StatCard icon={Zap} label={t('mine.statCapacity')} value={formatKw(capacity)} />
        </dl>
      )}
      <ul className="space-y-3">
        {data?.map((request) => (
          <li key={request.id}>
            <Link
              href={PATHS.household.request(request.id)}
              className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card transition hover:border-primary"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-semibold text-ink">{request.request_code}</span>
                  <StatusBadge status={request.status} />
                </div>
                <p className="mt-1 text-sm text-muted">
                  {joinParts([
                    `${request.monthly_units} ${t('common.units')}`,
                    formatKw(request.system_kw),
                    `${request.quotes_count} ${t('mine.quotes')}`,
                  ])}
                </p>
              </div>
              <ChevronRight aria-hidden className="size-5 shrink-0 text-muted" />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
