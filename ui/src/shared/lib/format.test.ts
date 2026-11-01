import { describe, expect, it } from 'vitest';
import { formatInr, formatKw, joinParts } from './format';

describe('format', () => {
  it('uses Indian digit grouping', () => {
    expect(formatInr(107000)).toBe('₹1,07,000');
    expect(formatInr(25740)).toBe('₹25,740');
  });

  it('leaves out missing parts', () => {
    expect(joinParts([null, '3 kW'])).toBe('3 kW');
    expect(joinParts(['Surat', undefined, '3 kW'])).toBe('Surat · 3 kW');
  });

  it('shows capacity without a needless decimal', () => {
    expect(formatKw(3)).toBe('3 kW');
    expect(formatKw(2.5)).toBe('2.5 kW');
  });
});
