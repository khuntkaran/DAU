/**
 * Live dictation through the browser's speech recognition. Chrome and Edge send
 * the audio to their speech service, so this needs an internet connection.
 */
import type { Lang } from '@/shared/types/common';
import type { SpeechFailure } from './types';

interface RecognitionAlternative {
  transcript: string;
}

interface RecognitionResult {
  isFinal: boolean;
  0: RecognitionAlternative;
}

interface RecognitionResultEvent {
  results: ArrayLike<RecognitionResult>;
}

interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type RecognitionConstructor = new () => Recognition;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

const SPEECH_LOCALES: Record<Lang, string> = { en: 'en-IN', hi: 'hi-IN', gu: 'gu-IN' };

const FAILURES: Record<string, SpeechFailure> = {
  'not-allowed': 'denied',
  'service-not-allowed': 'denied',
  'audio-capture': 'denied',
  'no-speech': 'no_speech',
  network: 'network',
  'language-not-supported': 'language',
};

function recognitionClass() {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export function isSpeechSupported() {
  return typeof window !== 'undefined' && recognitionClass() !== undefined;
}

interface DictationHandlers {
  onText: (text: string) => void;
  onEnd: (finalText: string) => void;
  onError: (failure: SpeechFailure) => void;
}

export function startDictation(lang: Lang, { onText, onEnd, onError }: DictationHandlers) {
  const Recognition = recognitionClass();
  if (!Recognition) throw new Error('Speech recognition is not supported.');

  const recognition = new Recognition();
  recognition.lang = SPEECH_LOCALES[lang];
  recognition.continuous = true;
  recognition.interimResults = true;

  let text = '';
  let failed = false;

  recognition.onresult = ({ results }) => {
    text = Array.from(results, (result) => result[0].transcript).join(' ').trim();
    onText(text);
  };
  recognition.onerror = ({ error }) => {
    failed = true;
    onError(FAILURES[error] ?? 'failed');
  };
  recognition.onend = () => {
    if (!failed) onEnd(text);
  };

  recognition.start();
  return { stop: () => recognition.stop() };
}
