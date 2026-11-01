'use client';

import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { ErrorState, Loading, PageTitle, StatusBadge } from '@/shared/ui/primitives';
import { QuoteComparison } from '@/tasks/compare-quotes/ui/QuoteComparison';
import { RoofAssessmentPanel } from '@/tasks/roof-assessment/ui/RoofAssessmentPanel';
import { EstimateCard } from '@/tasks/rule-sources/ui/EstimateCard';
import { getRequest } from '../api';

export function RequestDetailPage({ id }: { id: string }) {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(() => getRequest(id), [id]);

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState onRetry={reload} />;

  return (
    <div className="space-y-6">
      <PageTitle intro={data.address_text ?? data.district ?? undefined} actions={<StatusBadge status={data.status} />}>
        {data.request_code}
      </PageTitle>
      <EstimateCard estimate={data.estimate} />
      <RoofAssessmentPanel requestId={id} />
      <h2 className="pt-2 text-xl font-bold text-ink">{t('detail.quotes')}</h2>
      <QuoteComparison requestId={id} onAccepted={reload} />
    </div>
  );
}
