'use client';

import { Download, Star } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { downloadCsv, toCsv } from '@/shared/lib/csv';
import { Button, Card, EmptyState, ErrorState, Field, Loading, PageTitle } from '@/shared/ui/primitives';
import { listAdminVendors, updateVendor } from '../api';
import type { AdminVendor, VendorAction, VendorStatus } from '../types';

const STATUSES: VendorStatus[] = ['pending', 'verified', 'suspended', 'rejected'];

const STATUS_STYLES: Record<VendorStatus, string> = {
  pending: 'bg-sun-soft text-sun-strong',
  verified: 'bg-primary-soft text-primary-strong',
  suspended: 'bg-danger-soft text-danger',
  rejected: 'bg-canvas text-muted',
};

const ACTIONS: Record<VendorStatus, VendorAction[]> = {
  pending: ['verify', 'reject'],
  verified: ['suspend'],
  suspended: ['reinstate'],
  rejected: [],
};

export function VendorStatusBadge({ status }: { status: VendorStatus }) {
  const { t } = useI18n();
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {t(`vendorStatus.${status}`)}
    </span>
  );
}

export function AdminVendorsPage() {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(listAdminVendors, []);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<VendorStatus | ''>('');
  const [confirming, setConfirming] = useState<{ id: string; action: VendorAction } | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string>();

  const rows = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (data ?? []).filter(
      (vendor) =>
        (!status || vendor.verification_status === status) &&
        (!text || `${vendor.name} ${vendor.district}`.toLowerCase().includes(text)),
    );
  }, [data, query, status]);

  async function apply(vendor: AdminVendor, action: VendorAction) {
    setBusy(true);
    setActionError(undefined);
    try {
      await updateVendor(vendor.id, action);
      setConfirming(null);
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : t('common.error'));
    } finally {
      setBusy(false);
      reload();
    }
  }

  function exportRows() {
    const csv = toCsv(
      ['Vendor', 'District', 'Status', 'MNRE number', 'Rating', 'Installations', 'Quotes', 'Won'],
      rows.map((row) => [
        row.name,
        row.district,
        row.verification_status,
        row.mnre_registration_no,
        row.rating,
        row.installations_completed,
        row.quotes,
        row.quotes_won,
      ]),
    );
    downloadCsv('suryasetu-vendors.csv', csv);
  }

  return (
    <>
      <PageTitle
        intro={t('admin.vendorsIntro')}
        actions={
          <Button variant="secondary" disabled={rows.length === 0} onClick={exportRows}>
            <Download aria-hidden className="size-4" />
            {t('admin.exportCsv')}
          </Button>
        }
      >
        {t('nav.adminVendors')}
      </PageTitle>
      {loading && <Loading />}
      {error && <ErrorState onRetry={reload} />}
      {actionError && <div className="mb-4"><ErrorState message={actionError} /></div>}
      {data && (
        <Card className="p-0 sm:p-0">
          <div className="flex flex-wrap items-end gap-3 p-4">
            <Field
              className="min-w-48 flex-1"
              label={t('admin.searchVendors')}
              hideLabel
              placeholder={t('admin.searchVendors')}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <select
              aria-label={t('admin.filterStatus')}
              value={status}
              onChange={(event) => setStatus(event.target.value as VendorStatus | '')}
              className="min-h-11 rounded-xl border border-line bg-surface px-3 text-sm text-ink"
            >
              <option value="">{t('admin.allStatuses')}</option>
              {STATUSES.map((item) => (
                <option key={item} value={item}>
                  {t(`vendorStatus.${item}`)}
                </option>
              ))}
            </select>
          </div>
          {rows.length === 0 ? (
            <div className="p-4 pt-0">
              <EmptyState>{t('admin.noResults')}</EmptyState>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[60rem] text-left text-sm">
                <caption className="sr-only">{t('nav.adminVendors')}</caption>
                <thead className="border-y border-line bg-canvas text-xs tracking-wide text-muted uppercase">
                  <tr>
                    {['admin.colVendor', 'admin.colStatus', 'admin.colMnre', 'admin.colRating', 'admin.colInstalls', 'admin.colWon', 'admin.colAction'].map((key) => (
                      <th key={key} scope="col" className="px-4 py-2.5 font-semibold">
                        {t(key)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {rows.map((vendor) => (
                    <tr key={vendor.id} className="hover:bg-canvas/60">
                      <td className="px-4 py-3">
                        <span className="block font-semibold text-ink">{vendor.name}</span>
                        <span className="text-muted">{vendor.district}</span>
                      </td>
                      <td className="px-4 py-3"><VendorStatusBadge status={vendor.verification_status} /></td>
                      <td className="px-4 py-3 whitespace-nowrap text-ink">{vendor.mnre_registration_no ?? '—'}</td>
                      <td className="px-4 py-3 text-ink">
                        <span className="inline-flex items-center gap-1">
                          <Star aria-hidden className="size-3.5 fill-sun text-sun" />
                          {vendor.rating}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-ink">{vendor.installations_completed}</td>
                      <td className="px-4 py-3 text-ink">
                        {vendor.quotes_won} / {vendor.quotes}
                      </td>
                      <td className="px-4 py-3">
                        {confirming?.id === vendor.id ? (
                          <span className="flex gap-2">
                            <Button
                              variant={confirming.action === 'verify' || confirming.action === 'reinstate' ? 'primary' : 'danger'}
                              disabled={busy}
                              onClick={() => apply(vendor, confirming.action)}
                            >
                              {t('admin.confirm')} {t(`vendorAction.${confirming.action}`)}
                            </Button>
                            <Button variant="ghost" disabled={busy} onClick={() => setConfirming(null)}>
                              {t('compare.cancel')}
                            </Button>
                          </span>
                        ) : (
                          <span className="flex gap-2">
                            {ACTIONS[vendor.verification_status].map((action) => (
                              <Button
                                key={action}
                                variant="secondary"
                                aria-label={`${t(`vendorAction.${action}`)} ${vendor.name}`}
                                onClick={() => setConfirming({ id: vendor.id, action })}
                              >
                                {t(`vendorAction.${action}`)}
                              </Button>
                            ))}
                          </span>
                        )}
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
