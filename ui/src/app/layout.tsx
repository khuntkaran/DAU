import type { Metadata } from 'next';
import { Inter, Noto_Sans_Devanagari, Noto_Sans_Gujarati } from 'next/font/google';
import type { ReactNode } from 'react';
import { I18nProvider } from '@/shared/i18n/I18nProvider';
import { AppShell } from '@/shared/ui/AppShell';
import './globals.css';

const latin = Inter({ subsets: ['latin'], variable: '--font-latin', display: 'swap' });
const devanagari = Noto_Sans_Devanagari({
  subsets: ['devanagari'],
  variable: '--font-devanagari',
  display: 'swap',
  preload: false,
});
const gujarati = Noto_Sans_Gujarati({
  subsets: ['gujarati'],
  variable: '--font-gujarati',
  display: 'swap',
  preload: false,
});

export const metadata: Metadata = {
  title: 'SuryaSetu',
  description: 'Compare rooftop solar quotes under PM Surya Ghar with an AI assistant.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${latin.variable} ${devanagari.variable} ${gujarati.variable}`}>
      <body className="font-sans antialiased">
        <I18nProvider>
          <AppShell>{children}</AppShell>
        </I18nProvider>
      </body>
    </html>
  );
}
