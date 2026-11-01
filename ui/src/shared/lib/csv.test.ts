import { describe, expect, it } from 'vitest';
import { toCsv } from './csv';

describe('toCsv', () => {
  it('writes headers and rows', () => {
    expect(toCsv(['a', 'b'], [[1, 'x']])).toBe('a,b\r\n1,x');
  });

  it('quotes commas, quotes and new lines', () => {
    expect(toCsv(['a'], [['x, "y"']])).toBe('a\r\n"x, ""y"""');
  });

  it('leaves empty values blank', () => {
    expect(toCsv(['a', 'b'], [[null, true]])).toBe('a,b\r\n,true');
  });

  it('stops vendor text running as a spreadsheet formula', () => {
    expect(toCsv(['a'], [['=HYPERLINK("x")']])).toBe('a\r\n"\'=HYPERLINK(""x"")"');
  });
});
