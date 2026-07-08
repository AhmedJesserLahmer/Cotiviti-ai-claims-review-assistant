"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TimeseriesPoint } from "@/lib/types";

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: TimeseriesPoint;
}

function AnomalyDot({ cx, cy, payload }: DotProps) {
  if (cx == null || cy == null || !payload?.is_anomaly) return null;
  return (
    <circle cx={cx} cy={cy} r={6} fill="#ff5a5f" stroke="#2e1650" strokeWidth={2.5} />
  );
}

export default function AnomalyChart({ data }: { data: TimeseriesPoint[] }) {
  return (
    <div className="card-toon h-80 w-full p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#ede4ff" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fontWeight: 700, fill: "#2e1650" }}
            minTickGap={30}
            stroke="#2e1650"
          />
          <YAxis tick={{ fontSize: 10, fontWeight: 700, fill: "#2e1650" }} stroke="#2e1650" />
          <Tooltip
            contentStyle={{
              border: "2.5px solid #2e1650",
              borderRadius: "0.75rem",
              boxShadow: "3px 3px 0 0 #2e1650",
              fontWeight: 700,
            }}
          />
          <Line
            type="monotone"
            dataKey="daily_paid_total"
            stroke="#7e3ff2"
            strokeWidth={3}
            dot={<AnomalyDot />}
            activeDot={{ r: 5, fill: "#e5006e", stroke: "#2e1650", strokeWidth: 2 }}
            name="Daily Paid Total"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
