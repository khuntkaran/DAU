'use client';

import { useSyncExternalStore } from 'react';
import type { User } from '@/shared/types/common';

export interface Session {
  token: string;
  user: User;
}

const KEY = 'suryasetu.session';
const listeners = new Set<() => void>();

function readRaw(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function parse(raw: string | null): Session | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function readSession(): Session | null {
  return parse(readRaw());
}

export function writeSession(session: Session | null) {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch {
    // Private windows can refuse storage. The user simply stays signed out.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let cachedRaw: string | null = null;
let cachedSession: Session | null = null;

/** useSyncExternalStore needs a stable object while the stored value is unchanged. */
function snapshot(): Session | null {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cachedSession = parse(raw);
  }
  return cachedSession;
}

export function useSession(): Session | null {
  return useSyncExternalStore(subscribe, snapshot, () => null);
}
