import type { SolarRequest } from '@/shared/types/common';

export interface LatLng {
  lat: number;
  lng: number;
}

/** A place the map should move to: a device fix or a search result, never a dragged pin. */
export interface MapFocus extends LatLng {
  accuracy_m?: number;
}

export interface AddressResult extends LatLng {
  label: string;
}

export interface UploadedFile {
  file_id: string;
  url: string;
}

export interface NewRequestInput extends LatLng {
  location_source: SolarRequest['location_source'];
  address_text: string | null;
  monthly_units: number;
  budget_inr: number;
  roof_area_sqm: number;
  photo_file_id: string | null;
  input_method?: 'form' | 'voice';
}

/** The response holds the estimate and its citations straight away. */
export type NewRequestResponse = SolarRequest;
