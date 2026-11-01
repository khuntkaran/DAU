'use client';

import { CheckCircle2, ClipboardList, IndianRupee, ShieldAlert, Store, Zap } from 'lucide-react';
import Link from 'next/link';
import { PATHS } from '@/routes/paths';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatCount, formatDate, formatInr, formatKw, formatShortDate } from '@/shared/lib/format';
import { ErrorState, Loading, PageTitle, SectionCard, StatCard, buttonStyles } from '@/shared/ui/primitives';
import { getOverview } from '../api';
import { BarList, ColumnChart } from './charts';

export function AdminPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(getOverview, []);

  return (
    <>
      <PageTitle intro={t('admin.intro')}>{t('admin.title')}</PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {data && (
        <div className="space-y-6">
          {(data.vendors_pending > 0 || data.injection_flagged > 0) && (
            <div className="grid gap-3 md:grid-cols-2">
              {data.vendors_pending > 0 && (
                <Link href={PATHS.admin.vendors} className="flex items-center gap-3 rounded-2xl border border-sun/40 bg-sun-soft p-4 text-ink hover:border-sun">
                  <Store aria-hidden className="size-5 shrink-0 text-sun-strong" />
                  <span>
                    <strong>{data.vendors_pending}</strong> {t('admin.vendorsAwaiting')}
                  </span>
                </Link>
              )}
              {data.injection_flagged > 0 && (
                <Link href={PATHS.admin.review} className="flex items-center gap-3 rounded-2xl border border-danger/30 bg-danger-soft p-4 text-ink hover:border-danger">
                  <ShieldAlert aria-hidden className="size-5 shrink-0 text-danger" />
                  <span>
                    <strong>{data.injection_flagged}</strong> {t('admin.flagged')}
                  </span>
                </Link>
              )}
            </div>
          )}

          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={ClipboardList}
              label={t('admin.requests')}
              value={formatCount(data.requests)}
              hint={`${data.active_requests} ${t('admin.active')}`}
            />
            <StatCard
              icon={CheckCircle2}
              label={t('admin.acceptanceRate')}
              value={`${data.acceptance_rate_percent}%`}
              hint={`${formatCount(data.avg_quotes_per_request)} ${t('admin.quotesPerRequest')}`}
            />
            <StatCard
              icon={IndianRupee}
              label={t('admin.subsidyUnlocked')}
              value={formatInr(data.subsidy_unlocked_inr)}
              hint={t('admin.fromAccepted')}
            />
            <StatCard
              icon={Zap}
              label={t('admin.capacity')}
              value={formatKw(data.capacity_accepted_kw)}
              hint={`${data.vendors} ${t('admin.vendors')}`}
            />
          </dl>

          <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
            <SectionCard title={t('admin.chartWeekly')} description={t('admin.chartWeeklyHelp')}>
              <ColumnChart
                title={t('admin.chartWeekly')}
                valueLabel={t('admin.requests')}
                data={data.weekly.map(({ week_start: week, requests }) => ({
                  label: formatShortDate(week),
                  value: requests,
                }))}
              />
            </SectionCard>
            <SectionCard title={t('admin.chartStatus')}>
              <BarList
                title={t('admin.chartStatus')}
                valueLabel={t('admin.requests')}
                data={data.by_status.map(({ status, count }) => ({ label: t(`status.${status}`), value: count }))}
              />
            </SectionCard>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionCard title={t('admin.chartDistrict')}>
              <BarList
                title={t('admin.chartDistrict')}
                valueLabel={t('admin.requests')}
                data={data.by_district.map(({ district, requests }) => ({ label: district, value: requests }))}
              />
            </SectionCard>
            <SectionCard
              title={t('admin.activity')}
              action={
                <Link href={PATHS.admin.vendors} className={buttonStyles('secondary')}>
                  {t('admin.manageVendors')}
                </Link>
              }
            >
              <ol className="divide-y divide-line">
                {data.recent_activity.map((entry) => (
                  <li key={entry.id} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 py-2.5 text-sm">
                    <span className="text-ink">
                      {t(`audit.${entry.action}`)}: <strong>{entry.target}</strong>
                    </span>
                    <span className="text-muted">
                      {entry.actor} · {formatDate(entry.at)}
                    </span>
                  </li>
                ))}
              </ol>
            </SectionCard>
          </div>
        </div>
      )}
    </>
  );
}
