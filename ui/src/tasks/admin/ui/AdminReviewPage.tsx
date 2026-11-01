'use client';

import { ShieldAlert } from 'lucide-react';
import { useState } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatDate } from '@/shared/lib/format';
import { Button, Card, EmptyState, ErrorState, Loading, PageTitle } from '@/shared/ui/primitives';
import { listFlaggedQuotes, markQuoteReviewed, updateVendor } from '../api';
import type { FlaggedQuote } from '../types';
import { VendorStatusBadge } from './AdminVendorsPage';

export function AdminReviewPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(listFlaggedQuotes, []);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string>();

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setActionError(undefined);
    try {
      await action();
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : t('common.error'));
    } finally {
      setBusy(false);
      reload();
    }
  }

  const canSuspend = (item: FlaggedQuote) => item.vendor_status === 'verified';

  return (
    <>
      <PageTitle intro={t('admin.reviewIntro')}>{t('nav.adminReview')}</PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {actionError && <div className="mb-4"><ErrorState message={actionError} /></div>}
      {data?.length === 0 && <EmptyState>{t('admin.reviewEmpty')}</EmptyState>}
      <ul className="space-y-4">
        {data?.map((item) => (
          <li key={item.quote_id}>
            <Card>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex gap-3">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-danger-soft text-danger">
                    <ShieldAlert aria-hidden className="size-5" />
                  </span>
                  <div>
                    <h2 className="font-semibold text-ink">{item.vendor_name}</h2>
                    <p className="text-sm text-muted">
                      {item.quote_code} · {item.request_code} · {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>
                <VendorStatusBadge status={item.vendor_status} />
              </div>
              <blockquote className="mt-4 rounded-xl border-l-4 border-danger bg-danger-soft/50 p-3 text-sm text-ink">
                {item.excerpt}
              </blockquote>
              <p className="mt-2 text-sm text-muted">{t('admin.reviewNote')}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {item.reviewed ? (
                  <span className="text-sm font-semibold text-primary-strong">{t('admin.reviewed')}</span>
                ) : (
                  <Button variant="secondary" disabled={busy} onClick={() => run(() => markQuoteReviewed(item.quote_id))}>
                    {t('admin.markReviewed')}
                  </Button>
                )}
                {canSuspend(item) && (
                  <Button variant="danger" disabled={busy} onClick={() => run(() => updateVendor(item.vendor_id, 'suspend'))}>
                    {t('vendorAction.suspend')}
                  </Button>
                )}
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </>
  );
}
