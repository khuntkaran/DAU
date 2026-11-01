'use client';

import { CircleAlert, Inbox, LoaderCircle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react';
import { useId } from 'react';
import { useI18n } from '@/shared/i18n/I18nProvider';
import type { QuoteStatus, RequestStatus } from '@/shared/types/common';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-on-primary shadow-sm hover:bg-primary-strong',
  secondary: 'border border-line bg-surface text-ink shadow-sm hover:bg-canvas',
  ghost: 'text-muted hover:bg-canvas hover:text-ink',
  danger: 'bg-danger text-white shadow-sm hover:opacity-90',
};

/** Also used on links that look like buttons. */
export function buttonStyles(variant: ButtonVariant = 'primary') {
  return `inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_STYLES[variant]}`;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({ variant = 'primary', className = '', type = 'button', ...props }: ButtonProps) {
  return <button type={type} className={`${buttonStyles(variant)} ${className}`} {...props} />;
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-line bg-surface p-5 shadow-card sm:p-6 ${className}`}>{children}</section>;
}

interface SectionCardProps {
  title: string;
  description?: string;
  step?: number;
  action?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, description, step, action, children }: SectionCardProps) {
  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-1 gap-3">
          {step !== undefined && (
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-soft text-sm font-bold text-primary-strong">
              {step}
            </span>
          )}
          <div className="min-w-48 flex-1">
            <h2 className="text-lg font-semibold text-ink">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}

interface PageTitleProps {
  children: ReactNode;
  intro?: string | undefined;
  actions?: ReactNode;
}

export function PageTitle({ children, intro, actions }: PageTitleProps) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{children}</h1>
        {intro && <p className="mt-1 text-muted">{intro}</p>}
      </div>
      {actions}
    </header>
  );
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hideLabel?: boolean;
  help?: string | undefined;
  error?: string | undefined;
}

export function Field({ label, hideLabel = false, help, error, className = '', ...props }: FieldProps) {
  const id = useId();
  const messageId = `${id}-message`;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'mb-1.5 block text-sm font-medium text-ink'}>
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || help ? messageId : undefined}
        className="min-h-11 w-full rounded-xl border border-line bg-surface px-3 py-2 text-ink transition placeholder:text-muted focus:border-primary focus:outline-3 focus:outline-primary/15 disabled:bg-canvas disabled:text-muted aria-invalid:border-danger"
        {...props}
      />
      {(error || help) && (
        <p id={messageId} className={`mt-1.5 text-sm ${error ? 'text-danger' : 'text-muted'}`}>
          {error ?? help}
        </p>
      )}
    </div>
  );
}

const STATUS_STYLES: Partial<Record<RequestStatus | QuoteStatus, string>> = {
  open: 'bg-sun-soft text-sun-strong',
  quoted: 'bg-info-soft text-info',
  submitted: 'bg-info-soft text-info',
  accepted: 'bg-primary-soft text-primary-strong',
  completed: 'bg-primary-soft text-primary-strong',
  cancelled: 'bg-danger-soft text-danger',
};

export function StatusBadge({ status }: { status: RequestStatus | QuoteStatus }) {
  const { t } = useI18n();
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap ${STATUS_STYLES[status] ?? 'bg-canvas text-muted'}`}
    >
      <span aria-hidden className="size-1.5 rounded-full bg-current" />
      {t(`status.${status}`)}
    </span>
  );
}

export function Stat({ label, value, strong = false }: { label: ReactNode; value: ReactNode; strong?: boolean }) {
  return (
    <div>
      <dt className="text-sm text-muted">{label}</dt>
      <dd className={`mt-0.5 text-xl font-bold ${strong ? 'text-primary-strong' : 'text-ink'}`}>{value}</dd>
    </div>
  );
}

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  hint?: string | undefined;
}

export function StatCard({ icon: Icon, label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <dt className="text-sm font-medium text-muted">{label}</dt>
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary-strong">
          <Icon aria-hidden className="size-5" />
        </span>
      </div>
      <dd className="mt-2 text-2xl font-bold tracking-tight text-ink sm:text-3xl">{value}</dd>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}

export function Loading() {
  const { t } = useI18n();
  return (
    <div role="status" className="flex items-center justify-center gap-2 rounded-2xl border border-line bg-surface p-10 text-muted">
      <LoaderCircle aria-hidden className="size-5 animate-spin" />
      {t('common.loading')}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message?: string | undefined; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-danger/30 bg-danger-soft p-5 text-danger">
      <CircleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div>
        <p>{message ?? t('common.error')}</p>
        {onRetry && (
          <Button variant="secondary" className="mt-3" onClick={onRetry}>
            {t('common.retry')}
          </Button>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line bg-surface/60 p-10 text-center text-muted">
      <Inbox aria-hidden className="size-6" />
      {children}
    </div>
  );
}
