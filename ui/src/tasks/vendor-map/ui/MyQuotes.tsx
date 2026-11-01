'use client';

import Link from 'next/link';
import { PATHS } from '@/routes/paths';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatInr, formatKw, joinParts } from '@/shared/lib/format';
import { ErrorState, SectionCard, StatusBadge } from '@/shared/ui/primitives';
import { listMyQuotes } from '../api';

export function MyQuotes() {
  const { t } = useI18n();
  const { data, error, reload } = useAsync(listMyQuotes, []);

  if (error) return <ErrorState onRetry={reload} />;
  if (!data || data.length === 0) return null;

  return (
    <SectionCard title={t('vendor.myQuotes')}>
      <ul className="divide-y divide-line">
        {data.map((quote) => (
          <li key={quote.id}>
            <Link href={PATHS.vendor.request(quote.request_id)} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:text-primary-strong">
              <span>
                <span className="block font-semibold text-ink">{quote.request_code}</span>
                <span className="text-sm text-muted">
                  {joinParts([
                    quote.quote_code,
                    formatKw(quote.system_kw),
                    formatInr(quote.price_total_inr),
                    quote.contact_phone && `${t('quote.contact')}: ${quote.contact_phone}`,
                  ])}
                </span>
              </span>
              <StatusBadge status={quote.status} />
            </Link>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}
