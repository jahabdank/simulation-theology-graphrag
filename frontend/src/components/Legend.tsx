import { TYPE_COLORS, TYPE_LABELS } from "../styles/theme";

export default function Legend() {
  return (
    <div className="frosted absolute bottom-4 right-4 p-3 text-[11px]">
      <div className="text-[10px] uppercase tracking-widest mb-2 font-semibold"
        style={{ color: "#6B7280" }}>
        Entity Types
      </div>
      {Object.entries(TYPE_COLORS)
        .filter(([k]) => k !== "UNKNOWN")
        .map(([type, color]) => (
          <div key={type} className="flex items-center gap-2 mb-1">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ background: color, boxShadow: `0 0 6px ${color}55` }}
            />
            <span style={{ color: "#E5E7EB" }}>
              {TYPE_LABELS[type] || type}
            </span>
          </div>
        ))}
    </div>
  );
}
