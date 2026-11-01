'use client';

import { CheckCircle2, ImagePlus, LoaderCircle, LocateFixed, Search, TriangleAlert } from 'lucide-react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useCallback, useState } from 'react';
import type { FormEvent } from 'react';
import { PATHS } from '@/routes/paths';
import { useI18n } from '@/shared/i18n/I18nProvider';
import { formatDistance } from '@/shared/lib/format';
import { Button, ErrorState, Field, Loading, PageTitle, SectionCard, buttonStyles } from '@/shared/ui/primitives';
import { EstimateCard } from '@/tasks/rule-sources/ui/EstimateCard';
import type { VoiceFields } from '@/tasks/voice-input/types';
import { VoiceInput } from '@/tasks/voice-input/ui/VoiceInput';
import { createRequest, searchAddress, uploadFile } from '../api';
import { locateDevice } from '../location';
import type { AddressResult, LatLng, MapFocus, NewRequestResponse } from '../types';

const MapPicker = dynamic(() => import('./MapPicker'), { ssr: false, loading: () => <Loading /> });

/** Above this, the position cannot identify one roof. */
const ROOF_LEVEL_ACCURACY_M = 50;

interface FormErrors {
  location?: string;
  monthlyUnits?: string;
  budget?: string;
  roofArea?: string;
}

function isPositive(value: string) {
  return Number(value) > 0;
}

export function NewRequestPage() {
  const { t } = useI18n();
  const [point, setPoint] = useState<LatLng | null>(null);
  const [focus, setFocus] = useState<MapFocus | null>(null);
  const [accuracyM, setAccuracyM] = useState<number | null>(null);
  const [locationSource, setLocationSource] = useState<'map_pin' | 'gps' | 'search'>('map_pin');
  const [locating, setLocating] = useState(false);
  const [locationError, setLocationError] = useState<string>();
  const [searchText, setSearchText] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<AddressResult[] | null>(null);
  const [address, setAddress] = useState('');
  const [monthlyUnits, setMonthlyUnits] = useState('');
  const [budget, setBudget] = useState('');
  const [roofArea, setRoofArea] = useState('');
  const [photo, setPhoto] = useState<File | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<NewRequestResponse | null>(null);

  async function useMyLocation() {
    setLocationError(undefined);
    setLocating(true);
    try {
      await locateDevice({
        onImprove: ({ lat, lng, accuracy_m: accuracy }) => {
          setPoint({ lat, lng });
          setFocus({ lat, lng, accuracy_m: accuracy });
          setAccuracyM(accuracy);
          setLocationSource('gps');
        },
      });
    } catch (failure) {
      const reason = failure instanceof Error ? failure.message : 'unavailable';
      setLocationError(t(reason === 'denied' ? 'request.locationDenied' : 'request.locationUnavailable'));
    } finally {
      setLocating(false);
    }
  }

  // A pin placed by hand is exact, so the accuracy circle no longer applies.
  const placePin = useCallback((picked: LatLng) => {
    setPoint(picked);
    setAccuracyM(null);
    setLocationSource('map_pin');
  }, []);

  async function runSearch() {
    const query = searchText.trim();
    if (!query) return;
    setSearching(true);
    setLocationError(undefined);
    try {
      setSearchResults(await searchAddress(query));
    } catch {
      setSearchResults(null);
      setLocationError(t('request.searchFailed'));
    } finally {
      setSearching(false);
    }
  }

  function chooseResult(result: AddressResult) {
    const place = { lat: result.lat, lng: result.lng };
    setPoint(place);
    setFocus(place);
    setAccuracyM(null);
    setLocationSource('search');
    setAddress(result.label);
    setSearchResults(null);
  }

  function applyVoice(fields: VoiceFields) {
    if (fields.monthly_units !== null) setMonthlyUnits(String(fields.monthly_units));
    if (fields.budget_inr !== null) setBudget(String(fields.budget_inr));
    if (fields.roof_area_sqm !== null) setRoofArea(String(fields.roof_area_sqm));
  }

  function validate(): FormErrors {
    const found: FormErrors = {};
    if (!point) found.location = t('request.locationRequired');
    if (!isPositive(monthlyUnits)) found.monthlyUnits = t('request.positive');
    if (!isPositive(budget)) found.budget = t('request.positive');
    if (!isPositive(roofArea)) found.roofArea = t('request.positive');
    return found;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (!point || Object.keys(found).length > 0) return;

    setBusy(true);
    setSubmitError(undefined);
    try {
      const uploaded = photo ? await uploadFile(photo) : null;
      const request = await createRequest({
        ...point,
        location_source: locationSource,
        address_text: address.trim() || null,
        monthly_units: Number(monthlyUnits),
        budget_inr: Number(budget),
        roof_area_sqm: Number(roofArea),
        photo_file_id: uploaded?.file_id ?? null,
      });
      setCreated(request);
    } catch {
      setSubmitError(t('common.error'));
    } finally {
      setBusy(false);
    }
  }

  // An error stays only while its field is still wrong, so fixing a field clears it.
  const locationMessage = locationError ?? (point ? undefined : errors.location);
  const unitsError = isPositive(monthlyUnits) ? undefined : errors.monthlyUnits;
  const budgetError = isPositive(budget) ? undefined : errors.budget;
  const roofError = isPositive(roofArea) ? undefined : errors.roofArea;
  const lowAccuracy = !locating && accuracyM !== null && accuracyM > ROOF_LEVEL_ACCURACY_M;

  if (created) {
    return (
      <div className="space-y-6">
        <div className="flex items-start gap-3 rounded-2xl border border-primary/25 bg-primary-soft p-5">
          <CheckCircle2 aria-hidden className="mt-0.5 size-6 shrink-0 text-primary" />
          <div>
            <h1 className="text-xl font-bold text-ink">{t('request.posted')}</h1>
            <p className="text-muted">{created.request_code}</p>
          </div>
        </div>
        <EstimateCard estimate={created.estimate} />
        <Link href={PATHS.household.request(created.id)} className={buttonStyles('primary')}>
          {t('request.viewRequest')}
        </Link>
      </div>
    );
  }

  return (
    <>
      <PageTitle intro={t('request.intro')}>{t('request.title')}</PageTitle>
      <form onSubmit={submit} noValidate className="grid items-start gap-6 lg:grid-cols-[1.25fr_1fr]">
        <SectionCard
          step={1}
          title={t('request.location')}
          description={t('request.dragHint')}
          action={
            <Button variant="secondary" disabled={locating} onClick={useMyLocation}>
              {locating ? (
                <LoaderCircle aria-hidden className="size-4 animate-spin" />
              ) : (
                <LocateFixed aria-hidden className="size-4" />
              )}
              {t(locating ? 'request.locating' : 'request.useLocation')}
            </Button>
          }
        >
          <div className="mb-3 flex gap-2">
            <div className="min-w-0 flex-1">
              <Field
                label={t('request.search')}
                hideLabel
                placeholder={t('request.search')}
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    void runSearch();
                  }
                }}
              />
            </div>
            <Button variant="secondary" aria-label={t('request.searchButton')} disabled={searching} onClick={runSearch}>
              <Search aria-hidden className="size-4" />
            </Button>
          </div>
          {searchResults && (
            <ul className="mb-3 divide-y divide-line overflow-hidden rounded-xl border border-line">
              {searchResults.length === 0 && <li className="p-3 text-sm text-muted">{t('request.searchNone')}</li>}
              {searchResults.map((result) => (
                <li key={`${result.lat},${result.lng}`}>
                  <button
                    type="button"
                    onClick={() => chooseResult(result)}
                    className="w-full p-3 text-left text-sm text-ink hover:bg-canvas"
                  >
                    {result.label}
                  </button>
                </li>
              ))}
            </ul>
          )}

          <MapPicker
            value={point}
            focus={focus}
            accuracyM={accuracyM}
            onChange={placePin}
            streetLabel={t('request.mapStreet')}
            satelliteLabel={t('request.mapSatellite')}
          />

          <div aria-live="polite" className="mt-3 text-sm">
            {lowAccuracy && accuracyM !== null ? (
              <p className="flex gap-2 rounded-xl bg-sun-soft p-3 text-ink">
                <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-sun-strong" />
                <span>
                  <strong>
                    {t('request.accuracy')} {formatDistance(accuracyM)}.
                  </strong>{' '}
                  {t('request.lowAccuracy')}
                </span>
              </p>
            ) : (
              <p className={locationMessage ? 'text-danger' : 'text-muted'}>
                {locationMessage ??
                  (point
                    ? `${t('request.pinned')} ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}${
                        accuracyM === null ? '' : ` · ${t('request.accuracy')} ${formatDistance(accuracyM)}`
                      }`
                    : t('request.locationHelp'))}
              </p>
            )}
          </div>
          <Field
            className="mt-4"
            label={t('request.address')}
            value={address}
            onChange={(event) => setAddress(event.target.value)}
          />
        </SectionCard>

        <div className="space-y-6">
          <VoiceInput onFields={applyVoice} />
          <SectionCard step={2} title={t('request.detailsTitle')} description={t('request.detailsHelp')}>
            <div className="space-y-4">
              <Field
                label={t('request.units')}
                type="number"
                min="1"
                inputMode="numeric"
                value={monthlyUnits}
                error={unitsError}
                onChange={(event) => setMonthlyUnits(event.target.value)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  label={t('request.budget')}
                  type="number"
                  min="1"
                  inputMode="numeric"
                  value={budget}
                  error={budgetError}
                  onChange={(event) => setBudget(event.target.value)}
                />
                <Field
                  label={t('request.roof')}
                  type="number"
                  min="1"
                  inputMode="decimal"
                  value={roofArea}
                  error={roofError}
                  onChange={(event) => setRoofArea(event.target.value)}
                />
              </div>
              <Field
                label={t('request.photo')}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                help={t('request.photoHelp')}
                onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
              />
              {photo && (
                <p className="flex items-center gap-2 text-sm text-muted">
                  <ImagePlus aria-hidden className="size-4" />
                  {photo.name}
                </p>
              )}
            </div>
          </SectionCard>
          {submitError && <ErrorState message={submitError} />}
          <Button type="submit" className="w-full" disabled={busy}>
            {t('request.submit')}
          </Button>
        </div>
      </form>
    </>
  );
}
