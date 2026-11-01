type Cell = string | number | boolean | null;

function escapeCell(value: Cell): string {
  const text = value === null ? '' : String(value);
  // A leading = + - or @ would run as a formula when the file opens in Excel.
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text;
  return /[",\n\r]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

export function toCsv(headers: string[], rows: Cell[][]): string {
  return [headers, ...rows].map((row) => row.map(escapeCell).join(',')).join('\r\n');
}

export function downloadCsv(filename: string, csv: string) {
  // The byte order mark makes Excel read Hindi and Gujarati text correctly.
  const url = URL.createObjectURL(new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
