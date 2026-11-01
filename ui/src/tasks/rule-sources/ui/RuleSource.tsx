'use client';

import { useI18n } from '@/shared/i18n/I18nProvider';
import type { RuleCitation } from '../types';

/** The brief requires the app to show where each rule comes from. */
export function RuleSource({ citation }: { citation: RuleCitation | undefined }) {
  const { t } = useI18n();
  if (!citation) return null;
  const isEstimate = citation.status !== 'confirmed';
  return (
    <span className="text-sm text-muted">
      {isEstimate && (
        <span className="mr-2 rounded bg-sun-soft px-1.5 py-0.5 text-xs font-semibold text-sun-strong">
          {t('rule.estimate')}
        </span>
      )}
      {citation.url ? (
        <a
          href={citation.url}
          target="_blank"
          rel="noreferrer"
          className="text-info underline underline-offset-2"
          aria-label={`${t('rule.source')}: ${citation.source}`}
        >
          ⓘ {citation.source}
        </a>
      ) : (
        <span>ⓘ {citation.source}</span>
      )}
    </span>
  );
}
