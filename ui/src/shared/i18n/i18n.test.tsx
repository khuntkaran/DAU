import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import en from './en.json';
import gu from './gu.json';
import hi from './hi.json';
import { I18nProvider, useI18n } from './I18nProvider';

function Probe() {
  const { t, setLang } = useI18n();
  return (
    <>
      <p>{t('login.title')}</p>
      <p>{t('missing.key')}</p>
      <button onClick={() => setLang('gu')}>switch</button>
    </>
  );
}

describe('i18n', () => {
  it('has the same keys in all three languages', () => {
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
    expect(Object.keys(gu).sort()).toEqual(Object.keys(en).sort());
  });

  it('has no empty translations', () => {
    for (const messages of [en, hi, gu]) {
      expect(Object.values(messages).filter((text) => text.trim() === '')).toEqual([]);
    }
  });

  it('switches language, remembers it, and shows the key if a string is missing', async () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );
    expect(screen.getByText('Sign in')).toBeInTheDocument();
    expect(screen.getByText('missing.key')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'switch' }));

    expect(screen.getByText(gu['login.title'])).toBeInTheDocument();
    expect(localStorage.getItem('suryasetu.lang')).toBe('gu');
  });
});
