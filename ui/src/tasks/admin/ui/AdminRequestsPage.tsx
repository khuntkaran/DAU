'use client';

import { Download } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { downloadCsv, toCsv } from '@/shared/lib/csv';
import { formatDate, formatInr, formatKw } from '@/shared/lib/format';
import type { RequestStatus } from '@/shared/types/common';
import { Button, Card, EmptyState, ErrorState, Field, Loading, PageTitle, StatusBadge } from '@/shared/ui/primitives';
import { cancelRequest, listAdminRequests } from '../api';
import type { AdminRequest } from '../types';

const STATUSES: RequestStatus[] = ['open', 'quoted', 'accepted', 'completed', 'cancelled', 'expired'];

function isActive(request: AdminRequest) {
  return request.status === 'open' || request.status === 'quoted';
}

export function AdminRequestsPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(listAdminRequests, []);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<RequestStatus | ''>('');
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string>();

  const rows = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (data ?? []).filter(
      (request) =>
        (!status || request.status === status) &&
        (!text || `${request.request_code} ${request.district ?? ''}`.toLowerCase().includes(text)),
    );
  }, [data, query, status]);

  async function cancel(id: string) {
    setBusy(true);
    setActionError(undefined);
    try {
      await cancelRequest(id);
      setConfirmingId(null);
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : t('common.error'));
    } finally {
      setBusy(false);
      reload();
    }
  }

  function exportRows() {
    const csv = toCsv(
      ['Code', 'Status', 'District', 'Units', 'Budget', 'kW', 'Subsidy', 'Quotes', 'Created'],
      rows.map((row) => [
        row.request_code,
        row.status,
        row.district,
        row.monthly_units,
        row.budget_inr,
        row.suggested_kw,
        row.subsidy_inr,
        row.quote_count,
        row.created_at,
      ]),
    );
    downloadCsv('suryasetu-requests.csv', csv);
  }

  return (
    <>
      <PageTitle
        intro={t('admin.requestsIntro')}
        actions={
          <Button variant="secondary" disabled={rows.length === 0} onClick={exportRows}>
            <Download aria-hidden className="size-4" />
            {t('admin.exportCsv')}
          </Button>
        }
      >
        {t('nav.adminRequests')}
      </PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {actionError && <div className="mb-4"><ErrorState message={actionError} /></div>}
      {data && (
        <Card className="p-0 sm:p-0">
          <div className="flex flex-wrap items-end gap-3 p-4">
            <Field
              className="min-w-48 flex-1"
              label={t('admin.search')}
              hideLabel
              placeholder={t('admin.search')}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <label className="text-sm text-muted">
              <span className="sr-only">{t('admin.filterStatus')}</span>
              <select
                aria-label={t('admin.filterStatus')}
                value={status}
                onChange={(event) => setStatus(event.target.value as RequestStatus | '')}
                className="min-h-11 rounded-xl border border-line bg-surface px-3 text-ink"
              >
                <option value="">{t('admin.allStatuses')}</option>
                {STATUSES.map((item) => (
                  <option key={item} value={item}>
                    {t(`status.${item}`)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {rows.length === 0 ? (
            <div className="p-4 pt-0">
              <EmptyState>{t('admin.noResults')}</EmptyState>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[52rem] text-left text-sm">
                <caption className="sr-only">{t('nav.adminRequests')}</caption>
                <thead className="border-y border-line bg-canvas text-xs tracking-wide text-muted uppercase">
                  <tr>
                    {['admin.colRequest', 'admin.colStatus', 'admin.colDistrict', 'admin.colSystem', 'admin.colSubsidy', 'admin.colQuotes', 'admin.colCreated', 'admin.colAction'].map((key) => (
                      <th key={key} scope="col" className="px-4 py-2.5 font-semibold">
                        {t(key)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {rows.map((row) => (
                    <tr key={row.id} className="hover:bg-canvas/60">
                      <td className="px-4 py-3 font-semibold text-ink">{row.request_code}</td>
                      <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                      <td className="px-4 py-3 text-ink">{row.district ?? '—'}</td>
                      <td className="px-4 py-3 text-ink">{formatKw(row.suggested_kw)}</td>
                      <td className="px-4 py-3 text-ink">{formatInr(row.subsidy_inr)}</td>
                      <td className="px-4 py-3 text-ink">{row.quote_count}</td>
                      <td className="px-4 py-3 text-muted">{formatDate(row.created_at)}</td>
                      <td className="px-4 py-3">
                        {isActive(row) &&
                          (confirmingId === row.id ? (
                            <span className="flex gap-2">
                              <Button variant="danger" disabled={busy} onClick={() => cancel(row.id)}>
                                {t('admin.confirmCancel')}
                              </Button>
                              <Button variant="ghost" disabled={busy} onClick={() => setConfirmingId(null)}>
                                {t('compare.cancel')}
                              </Button>
                            </span>
                          ) : (
                            <Button variant="ghost" onClick={() => setConfirmingId(row.id)}>
                              {t('admin.cancelRequest')}
                            </Button>
                          ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
