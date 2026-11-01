'use client';

/** Single-series charts, one hue. Hover or focus shows the value; a hidden table reads to screen readers. */

export interface ChartPoint {
  label: string;
  value: number;
}

interface ChartProps {
  title: string;
  data: ChartPoint[];
  valueLabel: string;
}

function ChartTable({ title, data, valueLabel }: ChartProps) {
  return (
    <table className="sr-only">
      <caption>{title}</caption>
      <thead>
        <tr>
          <th scope="col">{title}</th>
          <th scope="col">{valueLabel}</th>
        </tr>
      </thead>
      <tbody>
        {data.map(({ label, value }) => (
          <tr key={label}>
            <td>{label}</td>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ColumnChart({ title, data, valueLabel }: ChartProps) {
  const max = Math.max(...data.map(({ value }) => value), 1);
  const lastIndex = data.length - 1;
  return (
    <>
      <div aria-hidden className="flex h-48 items-end gap-1 border-b border-line">
        {data.map(({ label, value }, index) => (
          <div key={label} className="group relative flex h-full flex-1 flex-col items-center justify-end">
            {(value === max || index === lastIndex) && value > 0 && (
              <span className="mb-1 text-xs font-semibold text-ink">{value}</span>
            )}
            <div
              className="w-full max-w-6 rounded-t bg-primary transition group-hover:bg-primary-strong"
              style={{ height: `${(value / max) * 82}%`, minHeight: value > 0 ? 4 : 0 }}
            />
            <div className="pointer-events-none absolute bottom-full z-10 mb-1 hidden rounded-lg bg-ink px-2 py-1 text-xs whitespace-nowrap text-white group-hover:block">
              {label}: {value} {valueLabel}
            </div>
          </div>
        ))}
      </div>
      <div aria-hidden className="mt-1.5 flex gap-1">
        {data.map(({ label }, index) => (
          <span key={label} className="flex-1 truncate text-center text-xs text-muted">
            {index % 2 === lastIndex % 2 ? label : ''}
          </span>
        ))}
      </div>
      <ChartTable title={title} data={data} valueLabel={valueLabel} />
    </>
  );
}

export function BarList({ title, data, valueLabel }: ChartProps) {
  const max = Math.max(...data.map(({ value }) => value), 1);
  return (
    <>
      <ul aria-hidden className="space-y-3">
        {data.map(({ label, value }) => (
          <li key={label} title={`${label}: ${value} ${valueLabel}`}>
            <div className="mb-1 flex justify-between gap-3 text-sm">
              <span className="truncate text-ink">{label}</span>
              <span className="font-semibold text-ink">{value}</span>
            </div>
            <div className="h-2 rounded-full bg-canvas">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(value / max) * 100}%`, minWidth: value > 0 ? 4 : 0 }}
              />
            </div>
          </li>
        ))}
      </ul>
      <ChartTable title={title} data={data} valueLabel={valueLabel} />
    </>
  );
}
