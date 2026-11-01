export interface RankingRow {
  quote_id: string;
  vendor_name: string;
  score: number;
  rank: number;
}

/** Ranking comes from code. The LLM only writes reasons, from the score table. */
export interface Recommendation {
  recommended_quote_id: string;
  ranking: RankingRow[];
  reasons: string[];
  caveats: string | null;
}
