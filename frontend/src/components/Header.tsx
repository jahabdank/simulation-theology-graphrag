import { ST } from "../styles/theme";
import type { StatsResponse } from "../types";

interface HeaderProps {
  stats: StatsResponse | null;
}

export default function Header({ stats }: HeaderProps) {
  return (
    <header>
      <div className="flex items-center gap-5 px-6 py-3"
        style={{ background: `linear-gradient(135deg, ${ST.navy} 0%, ${ST.navyLight} 100%)` }}>
        {/* Logo orb */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full shrink-0"
            style={{
              background: `radial-gradient(circle at 35% 35%, ${ST.blue}, ${ST.coral})`,
              boxShadow: `0 0 12px rgba(107, 140, 255, 0.4)`,
            }}
          />
          <h1 className="text-lg font-bold tracking-wide" style={{ color: ST.white }}>
            Simulation Theology
          </h1>
          <span className="text-sm font-medium opacity-70" style={{ color: ST.blue }}>
            Knowledge Graph
          </span>
        </div>

        <div className="flex-1" />

        {/* Stats badge */}
        {stats && (
          <div className="rounded-full px-4 py-1 text-xs whitespace-nowrap"
            style={{ background: ST.navy, border: `1px solid ${ST.border}` }}>
            <span className="font-semibold" style={{ color: ST.blue }}>{stats.total_nodes}</span>
            <span style={{ color: ST.textGrey }}> nodes  </span>
            <span className="font-semibold" style={{ color: ST.orange }}>{stats.total_edges}</span>
            <span style={{ color: ST.textGrey }}> edges</span>
          </div>
        )}
      </div>
      <div className="header-gradient-line" />
    </header>
  );
}
