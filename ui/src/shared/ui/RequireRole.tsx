'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { PATHS, ROLE_HOME } from '@/routes/paths';
import { useSession } from '@/shared/api/session';
import type { Role } from '@/shared/types/common';
import { Loading } from './primitives';

/** Client-side redirect for convenience. The API must still enforce every role. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const session = useSession();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  // The session lives in the browser, so it is unknown until after hydration.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!session) router.replace(PATHS.login);
    else if (session.user.role !== role) router.replace(ROLE_HOME[session.user.role]);
  }, [mounted, session, role, router]);

  if (!mounted || session?.user.role !== role) return <Loading />;
  return <>{children}</>;
}
