'use client';

import { Mic, Square } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { LANGUAGES, useI18n } from '@/shared/i18n/I18nProvider';
import type { Lang } from '@/shared/types/common';
import { Button, SectionCard } from '@/shared/ui/primitives';
import { parseVoiceFields } from '../parse';
import { isSpeechSupported, startDictation } from '../speech';
import type { SpeechFailure, VoiceFields } from '../types';

type Phase = 'idle' | 'listening' | 'done';

const FAILURE_KEYS: Record<SpeechFailure, string> = {
  denied: 'voice.denied',
  no_speech: 'voice.noSpeech',
  network: 'voice.network',
  language: 'voice.language_unsupported',
  failed: 'voice.failed',
};

export function VoiceInput({ onFields }: { onFields: (fields: VoiceFields) => void }) {
  const { t, lang: uiLang } = useI18n();
  const [lang, setLang] = useState<Lang>(uiLang);
  const [phase, setPhase] = useState<Phase>('idle');
  const [transcript, setTranscript] = useState('');
  const [foundAny, setFoundAny] = useState(false);
  const [error, setError] = useState<string>();
  const dictation = useRef<{ stop: () => void } | null>(null);

  useEffect(() => () => dictation.current?.stop(), []);

  function finish(text: string) {
    dictation.current = null;
    if (!text) {
      setError(t('voice.noSpeech'));
      setPhase('idle');
      return;
    }
    const fields = parseVoiceFields(text);
    setFoundAny(Object.values(fields).some((value) => value !== null));
    onFields(fields);
    setPhase('done');
  }

  function start() {
    setError(undefined);
    setTranscript('');
    if (!isSpeechSupported()) {
      setError(t('voice.unsupported'));
      return;
    }
    dictation.current = startDictation(lang, {
      onText: setTranscript,
      onEnd: finish,
      onError: (failure) => {
        dictation.current = null;
        setError(t(FAILURE_KEYS[failure]));
        setPhase('idle');
      },
    });
    setPhase('listening');
  }

  return (
    <SectionCard
      title={t('voice.title')}
      description={t('voice.help')}
      action={
        phase === 'listening' ? (
          <Button variant="secondary" onClick={() => dictation.current?.stop()}>
            <Square aria-hidden className="size-3.5 fill-danger text-danger" />
            {t('voice.stop')}
          </Button>
        ) : (
          <Button variant="secondary" onClick={start}>
            <Mic aria-hidden className="size-4" />
            {t('voice.start')}
          </Button>
        )
      }
    >
      <label className="flex items-center gap-2 text-sm text-muted">
        {t('voice.language')}
        <select
          value={lang}
          disabled={phase === 'listening'}
          onChange={(event) => setLang(event.target.value as Lang)}
          className="min-h-9 rounded-lg border border-line bg-surface px-2 text-ink"
        >
          {LANGUAGES.map(({ code, label }) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <div aria-live="polite" className="text-sm">
        {phase === 'listening' && (
          <p className="mt-3 rounded-xl bg-canvas p-3 text-ink">
            <span className="mr-2 inline-block size-2 animate-pulse rounded-full bg-danger" />
            {transcript || t('voice.listening')}
          </p>
        )}
        {error && <p className="mt-3 text-danger">{error}</p>}
        {phase === 'done' && (
          <div className={`mt-3 rounded-xl p-3 text-ink ${foundAny ? 'bg-primary-soft' : 'bg-sun-soft'}`}>
            <p>
              <span className="font-semibold">{t('voice.heard')}:</span> {transcript}
            </p>
            <p className="mt-1 font-semibold">{t(foundAny ? 'voice.confirm' : 'voice.noNumbers')}</p>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
