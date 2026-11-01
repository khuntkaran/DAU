const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const COUNT = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });

/** Indian digit grouping: ₹1,07,000. */
export function formatInr(amount: number): string {
  return `₹${INR.format(amount)}`;
}

export function formatCount(value: number): string {
  return COUNT.format(value);
}

/** Joins the parts that exist, so a missing value leaves no stray separator. */
export function joinParts(parts: (string | number | null | undefined)[]): string {
  return parts.filter((part) => part !== null && part !== undefined && part !== '').join(' · ');
}

export function formatKw(capacity: number): string {
  return `${capacity.toFixed(capacity % 1 === 0 ? 0 : 1)} kW`;
}

export function formatDistance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}
