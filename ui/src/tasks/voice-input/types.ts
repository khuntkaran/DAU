/** Prefills the form. The household always confirms before anything posts. */
export interface VoiceFields {
  monthly_units: number | null;
  budget_inr: number | null;
  roof_area_sqm: number | null;
}

export type SpeechFailure = 'denied' | 'no_speech' | 'network' | 'language' | 'failed';
