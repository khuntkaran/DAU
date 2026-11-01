import { apiRequest, IS_MOCK } from '@/shared/api/client';
import * as mock from './mock';
import type { RuleSet } from './types';

export function getCurrentRules(): Promise<RuleSet> {
  return IS_MOCK ? mock.getCurrentRules() : apiRequest('/rules/current');
}
