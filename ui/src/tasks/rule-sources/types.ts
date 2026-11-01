export interface RuleCitation {
  title: string;
  source: string;
  url: string | null;
  status: 'confirmed' | 'verify' | 'assumption';
}

export interface RuleSet {
  version: string;
  checked_on: string;
  citations: Record<string, RuleCitation>;
}
