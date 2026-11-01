'use client';

import { Sun } from 'lucide-react';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { useAsync } from '@/shared/hooks/useAsync';
import { formatInr, formatKw } from '@/shared/lib/format';
import type { Calculation } from '@/shared/types/common';
import { Card, Stat } from '@/shared/ui/primitives';
import { getCurrentRules } from '../api';
import { RuleSource } from './RuleSource';

export function EstimateCard({ estimate }: { estimate: Calculation }) {
  const { t } = useI18n();
  const rules = useAsync(getCurrentRules, []);
  const payback = estimate.payback_years === null ? '—' : `${estimate.payback_years} ${t('common.years')}`;

  return (
    <Card>
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-ink">
        <Sun aria-hidden className="size-5 text-sun" />
        {t('estimate.title')}
      </h2>
      <dl className="grid grid-cols-2 gap-4 rounded-xl bg-canvas p-4 md:grid-cols-5">
        <Stat label={t('estimate.size')} value={formatKw(estimate.system_kw)} />
        <Stat label={t('estimate.subsidy')} value={formatInr(estimate.subsidy_inr)} strong />
        <Stat label={t('estimate.netCost')} value={formatInr(estimate.net_cost_inr)} />
        <Stat label={t('estimate.saving')} value={formatInr(estimate.annual_saving_inr)} />
        <Stat label={t('estimate.payback')} value={payback} />
      </dl>
      <details className="mt-4 border-t border-line pt-3">
        <summary className="cursor-pointer text-sm font-semibold text-primary-strong">
          {t('estimate.howCalculated')}
        </summary>
        <ol className="mt-3 space-y-3">
          {estimate.steps.map((step) => (
            <li key={step.label}>
              <p className="text-sm text-ink">
                <span className="font-semibold">{step.label}:</span> {step.formula} = <strong>{step.value}</strong>
              </p>
              <RuleSource citation={rules.data?.citations[step.rule_key]} />
            </li>
          ))}
        </ol>
        <p className="mt-3 text-sm text-muted">{t('estimate.note')}</p>
      </details>
    </Card>
  );
}
