import { delay, getState, notFound } from '@/shared/mock/store';
import type { Recommendation } from './types';

export async function getRecommendation(requestId: string): Promise<Recommendation> {
  await delay(700);
  const quotes = getState()
    .quotes.map(({ quote }) => quote)
    .filter((quote) => quote.request_id === requestId)
    .sort((a, b) => (b.score?.total_score ?? 0) - (a.score?.total_score ?? 0));
  const winner = quotes[0];
  if (!winner) notFound();

  return {
    recommended_quote_id: winner.id,
    ranking: quotes.map((quote, index) => ({
      quote_id: quote.id,
      vendor_name: quote.vendor_name,
      score: quote.score?.total_score ?? 0,
      rank: index + 1,
    })),
    reasons: [
      `${winner.vendor_name} has the highest score, ${winner.score?.total_score.toFixed(1)} out of 100.`,
      `Its warranty is ${winner.warranty_panel_yrs} years on panels and ${winner.warranty_inverter_yrs} on the inverter.`,
      `It lists ${winner.review?.missing_items.length ?? 0} missing items.`,
    ],
    caveats: null,
  };
}
