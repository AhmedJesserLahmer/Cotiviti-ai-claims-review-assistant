import { TimeseriesPoint } from "@/lib/types";

export default function ProviderSparkline({ data }: { data: TimeseriesPoint[] }) {
  if (data.length === 0) {
    return <div className="h-10 w-full rounded-lg bg-cotiviti-lav/50" />;
  }

  const values = data.map((d) => d.daily_paid_total);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const W = 100;
  const H = 32;
  const step = W / Math.max(1, data.length - 1);

  const points = data
    .map((d, i) => {
      const x = i * step;
      const y = H - ((d.daily_paid_total - min) / range) * (H - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const anomalies = data
    .map((d, i) => ({ ...d, i }))
    .filter((d) => d.is_anomaly);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-10 w-full overflow-visible" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke="#7e3ff2"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      {anomalies.map((d) => {
        const x = d.i * step;
        const y = H - ((d.daily_paid_total - min) / range) * (H - 4) - 2;
        return (
          <circle
            key={d.date}
            cx={x}
            cy={y}
            r="2.6"
            fill="#ff5a5f"
            stroke="#2e1650"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        );
      })}
    </svg>
  );
}
