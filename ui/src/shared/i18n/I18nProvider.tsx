'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Lang } from '@/shared/types/common';
import en from './en.json';
import gu from './gu.json';
import hi from './hi.json';

type Messages = Record<string, string>;

const MESSAGES: Record<Lang, Messages> = { en, hi, gu };
const KEY = 'suryasetu.lang';

export const LANGUAGES: { code: Lang; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'gu', label: 'ગુજરાતી' },
];

interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function isLang(value: string | null): value is Lang {
  return value === 'en' || value === 'hi' || value === 'gu';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>('en');

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      // The server renders English, so the saved language can only apply after mount.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (isLang(saved)) setLangState(saved);
    } catch {
      // Storage can be blocked. English stays as the default.
    }
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // The choice still applies for this visit.
    }
  }, []);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      setLang,
      t: (key) => MESSAGES[lang][key] ?? MESSAGES.en[key] ?? key,
    }),
    [lang, setLang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error('useI18n must be used inside I18nProvider');
  return value;
}
