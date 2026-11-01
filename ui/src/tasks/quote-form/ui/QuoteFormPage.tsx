'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAsync } from '@/shared/hooks/useAsync';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatInr, formatKw } from '@/shared/lib/format';
import { Button, Card, ErrorState, Field, Loading, PageTitle, Stat, StatusBadge } from '@/shared/ui/primitives';
import type { LineItemType } from '@/tasks/compare-quotes/types';
import { getVendorRequest, submitQuote } from '../api';
import type { QuoteInput } from '../types';

const LINE_ITEMS: LineItemType[] = ['net_meter', 'mounting_structure', 'earthing', 'amc', 'insurance'];

const NUMBER_FIELDS = [
  { name: 'price_total_inr', labelKey: 'quote.price', required: true },
  { name: 'system_kw', labelKey: 'quote.systemKw', required: true },
  { name: 'panel_wattage', labelKey: 'quote.panelWattage', required: false },
  { name: 'inverter_kw', labelKey: 'quote.inverterKw', required: false },
  { name: 'warranty_panel_yrs', labelKey: 'quote.warrantyPanel', required: true },
  { name: 'warranty_inverter_yrs', labelKey: 'quote.warrantyInverter', required: false },
  { name: 'warranty_work_yrs', labelKey: 'quote.warrantyWork', required: false },
  { name: 'timeline_days', labelKey: 'quote.timeline', required: true },
] as const;

type NumberField = (typeof NUMBER_FIELDS)[number]['name'];
type TextField = 'panel_brand' | 'inverter_brand';
type FormField = NumberField | TextField;

function toInput(values: Partial<Record<FormField, string>>, dcr: string, items: LineItemType[], notes: string): QuoteInput {
  const optional = (name: NumberField) => (values[name] ? Number(values[name]) : null);
  return {
    price_total_inr: Number(values.price_total_inr),
    system_kw: Number(values.system_kw),
    panel_brand: values.panel_brand?.trim() ?? '',
    panel_wattage: optional('panel_wattage'),
    panel_is_dcr: dcr === '' ? null : dcr === 'yes',
    inverter_brand: values.inverter_brand?.trim() ?? '',
    inverter_kw: optional('inverter_kw'),
    warranty_panel_yrs: Number(values.warranty_panel_yrs),
    warranty_inverter_yrs: optional('warranty_inverter_yrs') ?? 0,
    warranty_work_yrs: optional('warranty_work_yrs') ?? 0,
    timeline_days: Number(values.timeline_days),
    included_items: items,
    notes,
  };
}

export function QuoteFormPage({ id }: { id: string }) {
  const { t } = useI18n();
  const { data, error, loading, reload } = useAsync(() => getVendorRequest(id), [id]);
  const [values, setValues] = useState<Partial<Record<FormField, string>>>({});
  const [dcr, setDcr] = useState('');
  const [items, setItems] = useState<LineItemType[]>([]);
  const [notes, setNotes] = useState('');
  const [invalid, setInvalid] = useState<FormField[]>([]);
  const [dcrChecked, setDcrChecked] = useState(false);
  const [submitError, setSubmitError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const set = (name: FormField, value: string) => setValues((current) => ({ ...current, [name]: value }));
  const isBlank = (name: FormField) => !values[name]?.trim() || values[name] === '0';
  // An error stays only while its field is still wrong, so fixing a field clears it.
  const fieldError = (name: FormField) => (invalid.includes(name) && isBlank(name) ? t('quote.required') : undefined);

  function toggle(item: LineItemType) {
    setItems((current) => (current.includes(item) ? current.filter((value) => value !== item) : [...current, item]));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const required: FormField[] = [
      ...NUMBER_FIELDS.filter((field) => field.required).map((field) => field.name),
      'panel_brand',
      'inverter_brand',
    ];
    const missing = required.filter(isBlank);
    setInvalid(missing);
    setDcrChecked(true);
    if (missing.length > 0 || dcr === '') return;

    setBusy(true);
    setSubmitError(undefined);
    try {
      await submitQuote(id, toInput(values, dcr, items, notes));
      reload();
    } catch (failure) {
      setSubmitError(failure instanceof Error ? failure.message : t('common.error'));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;
  if (error || !data) return <ErrorState onRetry={reload} />;

  return (
    <>
      <PageTitle intro={data.district ?? undefined}>{data.request_code}</PageTitle>
      <Card className="mb-4">
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label={t('request.units')} value={data.monthly_units} />
          <Stat label={t('request.budget')} value={formatInr(data.budget_inr)} />
          <Stat label={t('request.roof')} value={data.roof_area_sqm} />
          <Stat label={t('vendor.suggested')} value={formatKw(data.suggested_kw)} />
        </dl>
        <p className="mt-3 text-sm text-muted">{t('vendor.approx')}</p>
      </Card>

      {data.my_quote_status ? (
        <Card>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-bold text-ink">{t('quote.submitted')}</h2>
            <StatusBadge status={data.my_quote_status} />
          </div>
          {data.my_quote_status === 'accepted' && (
            <div className="mt-3 rounded-lg bg-primary-soft p-3 text-primary-strong">
              <p className="font-semibold">{t('quote.accepted')}</p>
              <p>
                {t('quote.contact')}: {data.household_phone}
              </p>
            </div>
          )}
        </Card>
      ) : (
        <form onSubmit={submit} noValidate>
          <Card>
            <h2 className="mb-4 text-lg font-bold text-ink">{t('quote.title')}</h2>
            <div className="grid gap-4 md:grid-cols-2">
              <Field
                label={t('quote.panelBrand')}
                value={values.panel_brand ?? ''}
                error={fieldError('panel_brand')}
                onChange={(event) => set('panel_brand', event.target.value)}
              />
              <Field
                label={t('quote.inverterBrand')}
                value={values.inverter_brand ?? ''}
                error={fieldError('inverter_brand')}
                onChange={(event) => set('inverter_brand', event.target.value)}
              />
              {NUMBER_FIELDS.map(({ name, labelKey }) => (
                <Field
                  key={name}
                  label={t(labelKey)}
                  type="number"
                  min="0"
                  step="any"
                  value={values[name] ?? ''}
                  error={fieldError(name)}
                  onChange={(event) => set(name, event.target.value)}
                />
              ))}
              <div>
                <label htmlFor="dcr" className="mb-1 block text-sm font-medium text-ink">
                  {t('quote.dcr')}
                </label>
                <select
                  id="dcr"
                  value={dcr}
                  onChange={(event) => setDcr(event.target.value)}
                  className="min-h-11 w-full rounded-lg border border-line bg-surface px-3 text-ink"
                >
                  <option value="">{t('quote.dcrChoose')}</option>
                  <option value="yes">{t('common.yes')}</option>
                  <option value="no">{t('common.no')}</option>
                </select>
                {dcrChecked && dcr === '' && <p className="mt-1.5 text-sm text-danger">{t('quote.required')}</p>}
              </div>
            </div>

            <fieldset className="mt-5">
              <legend className="mb-2 text-sm font-medium text-ink">{t('quote.included')}</legend>
              <div className="grid gap-2 md:grid-cols-2">
                {LINE_ITEMS.map((item) => (
                  <label key={item} className="flex min-h-9 items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={items.includes(item)}
                      onChange={() => toggle(item)}
                      className="size-4 accent-primary"
                    />
                    {t(`item.${item}`)}
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="mt-5">
              <label htmlFor="notes" className="mb-1 block text-sm font-medium text-ink">
                {t('quote.notes')}
              </label>
              <textarea
                id="notes"
                rows={3}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                className="w-full rounded-lg border border-line bg-surface p-3 text-ink"
              />
            </div>

            {submitError && (
              <div className="mt-4">
                <ErrorState message={submitError} />
              </div>
            )}
            <Button type="submit" className="mt-5 w-full md:w-auto" disabled={busy}>
              {t('quote.submit')}
            </Button>
          </Card>
        </form>
      )}
    </>
  );
}
