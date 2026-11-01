'use client';

import { FilePlus2, FileText, LayoutDashboard, LogOut, Map, ShieldAlert, Store, Sun } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import type { ReactNode } from 'react';
import { PATHS, ROLE_HOME, ROLE_NAV } from '@/routes/paths';
import type { NavIcon, NavItem } from '@/routes/paths';
import { IS_MOCK } from '@/shared/api/client';
import { useSession, writeSession } from '@/shared/api/session';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { LanguagePicker } from './LanguagePicker';

const NAV_ICONS: Record<NavIcon, LucideIcon> = {
  requests: FileText,
  new: FilePlus2,
  map: Map,
  dashboard: LayoutDashboard,
  vendors: Store,
  review: ShieldAlert,
};

function isCurrent(pathname: string, item: NavItem, home: string) {
  return item.href === home ? pathname === home : pathname.startsWith(item.href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const session = useSession();
  const pathname = usePathname();
  const router = useRouter();

  // The login page has its own full-screen layout.
  if (!session || pathname === PATHS.login) return <>{children}</>;

  const { role, full_name: fullName } = session.user;
  const home = ROLE_HOME[role];
  const nav = ROLE_NAV[role];

  function signOut() {
    writeSession(null);
    router.replace(PATHS.login);
  }

  const links = nav.map((item) => {
    const Icon = NAV_ICONS[item.icon];
    return (
      <Link
        key={item.href}
        href={item.href}
        aria-current={isCurrent(pathname, item, home) ? 'page' : undefined}
        className="flex min-h-10 shrink-0 items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium whitespace-nowrap text-on-sidebar-muted transition hover:bg-sidebar-raised hover:text-on-sidebar aria-[current=page]:bg-sidebar-raised aria-[current=page]:text-on-sidebar"
      >
        <Icon aria-hidden className="size-5 shrink-0" />
        {t(item.labelKey)}
      </Link>
    );
  });

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh flex-col bg-sidebar p-4 lg:flex">
        <Link href={home} className="mb-8 flex items-center gap-3 px-2 py-1 text-on-sidebar">
          <span className="grid size-9 place-items-center rounded-xl bg-sun text-sidebar">
            <Sun aria-hidden className="size-5" />
          </span>
          <span className="text-lg font-bold">{t('app.name')}</span>
        </Link>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {links}
        </nav>
        <div className="mt-auto border-t border-white/10 pt-4">
          <p className="truncate px-3 text-sm font-semibold text-on-sidebar">{fullName}</p>
          <p className="px-3 text-xs text-on-sidebar-muted">{t(`role.${role}`)}</p>
          <button
            onClick={signOut}
            className="mt-2 flex min-h-10 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-on-sidebar-muted transition hover:bg-sidebar-raised hover:text-on-sidebar"
          >
            <LogOut aria-hidden className="size-5" />
            {t('nav.signOut')}
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <div className="bg-sidebar px-4 py-3 lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <Link href={home} className="flex items-center gap-2 text-on-sidebar">
              <Sun aria-hidden className="size-5 text-sun" />
              <span className="font-bold">{t('app.name')}</span>
            </Link>
            <button onClick={signOut} aria-label={t('nav.signOut')} className="grid size-10 place-items-center text-on-sidebar-muted">
              <LogOut aria-hidden className="size-5" />
            </button>
          </div>
          <nav aria-label="Main mobile" className="mt-2 flex gap-1 overflow-x-auto">
            {links}
          </nav>
        </div>

        <header className="flex items-center justify-end gap-3 border-b border-line bg-surface px-4 py-2.5 sm:px-8">
          {IS_MOCK && (
            <span className="mr-auto rounded-full bg-sun-soft px-2.5 py-1 text-xs font-semibold text-sun-strong">
              {t('app.mockData')}
            </span>
          )}
          <LanguagePicker />
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-8 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
