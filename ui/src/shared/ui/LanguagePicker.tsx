'use client';

import { LANGUAGES, useI18n } from '@/shared/i18n/I18nProvider';
import type { Lang } from '@/shared/types/common';

export function LanguagePicker() {
  const { t, lang, setLang } = useI18n();
  return (
    <select
      aria-label={t('voice.language')}
      value={lang}
      onChange={(event) => setLang(event.target.value as Lang)}
      className="min-h-9 rounded-lg border border-line bg-surface px-2 text-sm text-ink"
    >
      {LANGUAGES.map(({ code, label }) => (
        <option key={code} value={code}>
          {label}
        </option>
      ))}
    </select>
  );
}
