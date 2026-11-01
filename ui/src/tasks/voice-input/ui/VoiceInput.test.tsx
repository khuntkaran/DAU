import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { VoiceInput } from './VoiceInput';

class FakeRecognition {
  static last: FakeRecognition;
  lang = '';
  continuous = false;
  interimResults = false;
  onresult: ((event: { results: { isFinal: boolean; 0: { transcript: string } }[] }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  constructor() {
    FakeRecognition.last = this;
  }
  start() {}
  stop() {
    this.onend?.();
  }
  say(transcript: string) {
    act(() => this.onresult?.({ results: [{ isFinal: true, 0: { transcript } }] }));
  }
  fail(error: string) {
    act(() => this.onerror?.({ error }));
  }
}

function setup(onFields = vi.fn()) {
  render(
    <I18nProvider>
      <VoiceInput onFields={onFields} />
    </I18nProvider>,
  );
  return onFields;
}

const start = () => userEvent.click(screen.getByRole('button', { name: 'Start speaking' }));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('VoiceInput', () => {
  it('explains when the browser has no speech recognition', async () => {
    setup();
    await start();
    expect(screen.getByText(/Voice is not available in this browser/)).toBeInTheDocument();
  });

  it('uses the chosen language', async () => {
    vi.stubGlobal('webkitSpeechRecognition', FakeRecognition);
    setup();
    await userEvent.selectOptions(screen.getByRole('combobox'), 'gu');
    await start();
    expect(FakeRecognition.last.lang).toBe('gu-IN');
  });

  it('fills the form with what was actually said', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    const onFields = setup();
    await start();
    FakeRecognition.last.say('I use 512 units and my budget is 3 lakh');
    expect(screen.getByText('I use 512 units and my budget is 3 lakh')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Stop' }));

    expect(onFields).toHaveBeenCalledWith({ monthly_units: 512, budget_inr: 300000, roof_area_sqm: null });
    expect(screen.getByText(/We filled in the form/)).toBeInTheDocument();
  });

  it('says so when it heard no numbers, and invents nothing', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    const onFields = setup();
    await start();
    FakeRecognition.last.say('hello there');
    await userEvent.click(screen.getByRole('button', { name: 'Stop' }));

    expect(onFields).toHaveBeenCalledWith({ monthly_units: null, budget_inr: null, roof_area_sqm: null });
    expect(screen.getByText(/did not hear any numbers/)).toBeInTheDocument();
  });

  it.each([
    ['not-allowed', /Microphone access was blocked/],
    ['no-speech', /did not hear anything/],
    ['network', /needs an internet connection/],
    ['language-not-supported', /does not support this language/],
  ])('explains the %s error', async (code, message) => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    const onFields = setup();
    await start();
    FakeRecognition.last.fail(code);
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(onFields).not.toHaveBeenCalled();
  });

  it('reports silence as no speech', async () => {
    vi.stubGlobal('SpeechRecognition', FakeRecognition);
    const onFields = setup();
    await start();
    await userEvent.click(screen.getByRole('button', { name: 'Stop' }));
    expect(screen.getByText(/did not hear anything/)).toBeInTheDocument();
    expect(onFields).not.toHaveBeenCalled();
  });
});
