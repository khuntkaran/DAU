'use client';

import { useEffect } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatKw } from '@/shared/lib/format';
import { Card, Stat } from '@/shared/ui/primitives';
import { getAssessment } from '../api';
import type { RoofAssessment } from '../types';

const POLL_MS = 2000;

function PhotoWithBoxes({ assessment }: { assessment: RoofAssessment }) {
  const { t } = useI18n();
  if (!assessment.photo_url) return null;
  return (
    <div className="relative overflow-hidden rounded-lg">
      {/* Photos come from object storage at runtime, so next/image sizing does not apply. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={assessment.photo_url} alt={t('request.photo')} className="w-full" />
      {assessment.obstructions.map((box) => (
        <div
          key={box.id}
          className="absolute border-2 border-sun bg-sun/15"
          style={{
            left: `${box.bbox_x * 100}%`,
            top: `${box.bbox_y * 100}%`,
            width: `${box.bbox_w * 100}%`,
            height: `${box.bbox_h * 100}%`,
          }}
        >
          <span className="absolute left-0 top-0 bg-sun px-1 text-xs font-semibold text-ink">
            {t(`roof.${box.obstruction_type}`)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function RoofAssessmentPanel({ requestId }: { requestId: string }) {
  const { t } = useI18n();
  const { data, error, reload } = useAsync(() => getAssessment(requestId), [requestId]);
  const pending = data?.status === 'pending';

  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(reload, POLL_MS);
    return () => clearTimeout(timer);
  }, [pending, data, reload]);

  // AI never blocks the page: a failure only replaces this one panel.
  const failed = Boolean(error) || data?.status === 'failed';

  return (
    <Card>
      <h2 className="mb-3 text-lg font-semibold text-ink">{t('roof.title')}</h2>
      {failed && <p className="text-muted">{t('roof.failed')}</p>}
      {pending && (
        <p role="status" className="animate-pulse text-muted">
          {t('roof.pending')}
        </p>
      )}
      {data?.status === 'done' && (
        <div className="grid gap-4 md:grid-cols-2">
          <PhotoWithBoxes assessment={data} />
          <div>
            {data.summary && <p className="mb-3 text-ink">{data.summary}</p>}
            <dl className="grid grid-cols-2 gap-3">
              <Stat label={t('roof.usableArea')} value={`${data.usable_area_sqm} m²`} />
              <Stat label={t('roof.maxKw')} value={formatKw(data.max_kw_by_area ?? 0)} />
              {data.shade_risk && <Stat label={t('roof.shade')} value={t(`severity.${data.shade_risk}`)} />}
            </dl>
            <h3 className="mt-4 text-sm font-semibold text-ink">{t('roof.obstructions')}</h3>
            <ul className="mt-1 space-y-1 text-sm text-muted">
              {data.obstructions.map((item) => (
                <li key={item.id}>
                  {t(`roof.${item.obstruction_type}`)} · {t(`severity.${item.severity}`)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Card>
  );
}
