import { apiRequest, ApiError, IS_MOCK } from '@/shared/api/client';
import type { Schemas } from '@/shared/api/mappers';
import { listQuotes } from '@/tasks/compare-quotes/api';
import * as mock from './mock';
import type { Recommendation } from './types';

/**
 * Ranking is calculated in code and is always available. The reasons need the
 * AI job, which is not built yet, so they stay empty rather than being invented.
 */
async function rankFromScores(requestId: string): Promise<Recommendation> {
  const quotes = await listQuotes(requestId);
  const top = quotes[0];
  if (!top) throw new ApiError(404, 'no_quotes', 'There are no quotes to compare.');
  return {
    recommended_quote_id: top.id,
    ranking: quotes.map((quote, index) => ({
      quote_id: quote.id,
      vendor_name: quote.vendor_name,
      score: quote.score?.total_score ?? 0,
      rank: index + 1,
    })),
    reasons: [],
    caveats: null,
  };
}

export async function getRecommendation(requestId: string): Promise<Recommendation> {
  if (IS_MOCK) return mock.getRecommendation(requestId);
  const ranked = await rankFromScores(requestId);
  try {
    await apiRequest<Schemas['JobAccepted']>(`/requests/${requestId}/recommendation`, { method: 'POST' });
    const result = await apiRequest<Schemas['RecommendationOut']>(`/requests/${requestId}/recommendation`);
    return { ...ranked, recommended_quote_id: result.recommended_quote_id, reasons: result.reasons, caveats: result.caveats };
  } catch (failure) {
    if (failure instanceof ApiError && (failure.status === 501 || failure.status === 404)) return ranked;
    throw failure;
  }
}
