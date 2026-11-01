'use client';

import { BadgeCheck, Calculator, MessagesSquare, ShieldCheck, Sun } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ROLE_HOME } from '@/routes/paths';
import { ApiError, IS_MOCK } from '@/shared/api/client';
import { useSession, writeSession } from '@/shared/api/session';
import { useI18n } from '@/shared/i18n/I18nProvider';
import type { Role } from '@/shared/types/common';
import { LanguagePicker } from '@/shared/ui/LanguagePicker';
import { Button, Field } from '@/shared/ui/primitives';
import { requestOtp, verifyOtp } from '../api';
import { DEMO_PHONES } from '../types';

const DEMO_ROLES: { role: Role; labelKey: string }[] = [
  { role: 'household', labelKey: 'login.asHousehold' },
  { role: 'vendor', labelKey: 'login.asVendor' },
  { role: 'admin', labelKey: 'login.asAdmin' },
];

const FEATURES = [
  { icon: Calculator, titleKey: 'login.feature1' },
  { icon: BadgeCheck, titleKey: 'login.feature2' },
  { icon: MessagesSquare, titleKey: 'login.feature3' },
];

const ERROR_KEYS: Record<string, string> = {
  invalid_code: 'login.invalidCode',
  otp_expired: 'login.codeExpired',
  too_many_attempts: 'login.tooManyAttempts',
  account_suspended: 'login.suspended',
};

export function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const session = useSession();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (session) router.replace(ROLE_HOME[session.user.role]);
  }, [session, router]);

  async function sendCode(toPhone: string) {
    setBusy(true);
    setError(undefined);
    setCode('');
    try {
      await requestOtp({ phone: toPhone });
      setPhone(toPhone);
      setCodeSent(true);
    } catch {
      setError(t('common.error'));
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    setError(undefined);
    try {
      writeSession(await verifyOtp({ phone, code }));
    } catch (failure) {
      const key = failure instanceof ApiError ? ERROR_KEYS[failure.code] : undefined;
      setError(t(key ?? 'common.error'));
      if (failure instanceof ApiError && failure.code !== 'invalid_code') setCodeSent(false);
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (codeSent) {
      await verify();
    } else if (/^\d{10}$/.test(phone)) {
      await sendCode(phone);
    } else {
      setError(t('login.invalidPhone'));
    }
  }

  function startOver() {
    setCodeSent(false);
    setCode('');
    setError(undefined);
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-[1.1fr_1fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-12 text-on-sidebar lg:flex">
        <div aria-hidden className="absolute -right-40 -top-40 size-[34rem] rounded-full bg-sun/15 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-sun text-sidebar">
            <Sun aria-hidden className="size-6" />
          </span>
          <span className="text-xl font-bold">{t('app.name')}</span>
        </div>
        <div className="relative max-w-lg">
          <h2 className="text-4xl leading-tight font-bold tracking-tight">{t('login.heroTitle')}</h2>
          <p className="mt-4 text-lg text-on-sidebar-muted">{t('app.tagline')}</p>
          <ul className="mt-10 space-y-4">
            {FEATURES.map(({ icon: Icon, titleKey }) => (
              <li key={titleKey} className="flex items-center gap-3">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-white/10">
                  <Icon aria-hidden className="size-5 text-sun" />
                </span>
                {t(titleKey)}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-on-sidebar-muted">{t('login.schemeNote')}</p>
      </aside>

      <main className="flex flex-col bg-surface px-6 py-6 sm:px-12">
        <header className="flex justify-end">
          <LanguagePicker />
        </header>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-8">
          <span className="mb-6 grid size-11 place-items-center rounded-xl bg-primary-soft text-primary-strong lg:hidden">
            <Sun aria-hidden className="size-6" />
          </span>
          <h1 className="text-3xl font-bold tracking-tight text-ink">{t('login.title')}</h1>
          <p className="mt-2 text-muted">{t(codeSent ? 'login.codeSentTo' : 'login.subtitle')}</p>

          <form onSubmit={submit} noValidate className="mt-8 space-y-4">
            <Field
              label={t('login.phone')}
              type="tel"
              inputMode="numeric"
              autoComplete="tel"
              value={phone}
              disabled={codeSent}
              error={codeSent ? undefined : error}
              onChange={(event) => setPhone(event.target.value)}
            />
            {codeSent && (
              <Field
                label={t('login.code')}
                inputMode="numeric"
                autoComplete="one-time-code"
                autoFocus
                help={IS_MOCK ? t('login.demoHint') : undefined}
                value={code}
                error={error}
                onChange={(event) => setCode(event.target.value)}
              />
            )}
            <Button type="submit" className="w-full" disabled={busy}>
              {t(codeSent ? 'login.verify' : 'login.sendOtp')}
            </Button>
            {codeSent && (
              <Button variant="ghost" className="w-full" onClick={startOver}>
                {t('login.useOther')}
              </Button>
            )}
          </form>

          {IS_MOCK && !codeSent && (
            <div className="mt-8 rounded-xl border border-line bg-canvas p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                <ShieldCheck aria-hidden className="size-4 text-primary" />
                {t('login.quick')}
              </p>
              <p className="mt-1 text-sm text-muted">{t('login.quickHelp')}</p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {DEMO_ROLES.map(({ role, labelKey }) => (
                  <Button key={role} variant="secondary" disabled={busy} onClick={() => sendCode(DEMO_PHONES[role])}>
                    {t(labelKey)}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
