import { Tags, TrendingUp, Users, Radar, FileText } from "lucide-react";
import RiskBadge from "./RiskBadge";

const ROWS = [
  { id: "CLM00000", risk: "Low" },
  { id: "CLM00001", risk: "High" },
  { id: "CLM00002", risk: "Medium" },
];

const SIGNAL_TILES = [
  { Icon: Tags, color: "bg-cotiviti-violet" },
  { Icon: TrendingUp, color: "bg-cotiviti-teal" },
  { Icon: Users, color: "bg-cotiviti-gold" },
  { Icon: Radar, color: "bg-cotiviti-magenta" },
];

export default function AppMockup() {
  return (
    <div className="hidden shrink-0 lg:block" aria-hidden="true">
      <div className="relative rotate-6 transition-transform duration-300 hover:rotate-2">
        <div className="card-toon w-80 overflow-hidden bg-white">
          {/* browser chrome */}
          <div className="flex items-center gap-1.5 border-b-[3px] border-cotiviti-ink bg-cotiviti-lav px-3 py-2">
            <span className="h-2.5 w-2.5 rounded-full border-2 border-cotiviti-ink bg-cotiviti-coral" />
            <span className="h-2.5 w-2.5 rounded-full border-2 border-cotiviti-ink bg-cotiviti-gold" />
            <span className="h-2.5 w-2.5 rounded-full border-2 border-cotiviti-ink bg-cotiviti-teal" />
            <span className="ml-2 flex-1 truncate rounded-full border-2 border-cotiviti-ink bg-white px-2 py-0.5 text-[10px] font-bold text-cotiviti-ink/60">
              cotiviti.ai/claims
            </span>
          </div>

          <div className="space-y-3 p-3">
            {/* mini signal tiles */}
            <div className="grid grid-cols-4 gap-1.5">
              {SIGNAL_TILES.map(({ Icon, color }, i) => (
                <span
                  key={i}
                  className={`grid h-7 place-items-center rounded-lg border-2 border-cotiviti-ink text-white ${color}`}
                >
                  <Icon size={12} strokeWidth={3} />
                </span>
              ))}
            </div>

            {/* mini sparkline card */}
            <div className="rounded-xl border-2 border-cotiviti-ink bg-cotiviti-cream p-2">
              <svg viewBox="0 0 100 28" className="h-7 w-full overflow-visible">
                <polyline
                  points="0,20 12,16 24,18 36,8 48,14 60,6 72,12 84,4 100,10"
                  fill="none"
                  stroke="#7e3ff2"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="84" cy="4" r="3" fill="#ff5a5f" stroke="#2e1650" strokeWidth="1.5" />
              </svg>
            </div>

            {/* mini claims rows */}
            <div className="space-y-1.5">
              {ROWS.map((row) => (
                <div
                  key={row.id}
                  className="flex items-center justify-between rounded-lg bg-cotiviti-lav/60 px-2 py-1.5"
                >
                  <span className="flex items-center gap-1 text-[10px] font-extrabold text-cotiviti-purple">
                    <FileText size={11} strokeWidth={3} />
                    {row.id}
                  </span>
                  <RiskBadge label={row.risk} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* little floating sparkle accents for a hand-drawn feel */}
        <span className="absolute -right-3 -top-3 text-2xl">✨</span>
      </div>
    </div>
  );
}
