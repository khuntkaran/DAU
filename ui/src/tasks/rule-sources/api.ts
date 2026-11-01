import { apiRequest, IS_MOCK } from '@/shared/api/client';
import type { Schemas } from '@/shared/api/mappers';
import * as mock from './mock';
import type { RuleSet } from './types';

export async function getCurrentRules(): Promise<RuleSet> {
  if (IS_MOCK) return mock.getCurrentRules();
  const rules = await apiRequest<Schemas['RulesOut']>('/rules/current');
  return {
    version: rules.version,
    checked_on: rules.checked_on,
    citations: Object.fromEntries(rules.citations.map(({ key, ...citation }) => [key, citation])),
  };
}
