import type { RequestStatus, SolarRequest } from '@/shared/types/common';

export type MyRequest = SolarRequest;

/** A row in the household's list. Full details load on the request page. */
export interface RequestListItem {
  id: string;
  request_code: string;
  status: RequestStatus;
  monthly_units: number;
  system_kw: number;
  quotes_count: number;
  created_at: string;
}
