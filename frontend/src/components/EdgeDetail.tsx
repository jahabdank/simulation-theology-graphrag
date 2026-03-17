import ReactMarkdown from "react-markdown";
import { ST } from "../styles/theme";

interface EdgeDetailProps {
  source: string;
  target: string;
  edgeData: { weight: number; description: string; keywords: string } | null;
}

export default function EdgeDetail({ source, target, edgeData }: EdgeDetailProps) {
  if (!edgeData) return null;

  const barWidth = Math.min((edgeData.weight / 6) * 100, 100);
  const keywords = edgeData.keywords
    ? edgeData.keywords.split(",").map((k) => k.trim()).filter(Boolean)
    : [];

  return (
    <div>
      {/* Relationship header */}
      <div className="p-4 rounded-xl mb-4"
        style={{
          background: `linear-gradient(135deg, ${ST.navy} 0%, ${ST.blue}15 100%)`,
          border: `1px solid ${ST.border}`,
        }}>
        <div className="text-[10px] uppercase tracking-widest mb-3" style={{ color: ST.textGrey }}>
          Relationship
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-base font-bold" style={{ color: ST.blue }}>{source}</span>
          <span className="text-lg" style={{ color: ST.textGrey }}>{"\u2192"}</span>
          <span className="text-base font-bold" style={{ color: ST.orange }}>{target}</span>
        </div>
      </div>

      {/* Weight bar */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className="text-[11px]" style={{ color: ST.textGrey }}>Weight</span>
          <span className="text-[11px]" style={{ color: ST.textLight }}>{edgeData.weight.toFixed(1)}</span>
        </div>
        <div className="weight-bar-track">
          <div className="weight-bar-fill" style={{ width: `${barWidth}%` }} />
        </div>
      </div>

      {/* Keywords */}
      {keywords.length > 0 && (
        <div className="mb-4">
          {keywords.map((kw) => (
            <span key={kw} className="keyword-pill">{kw}</span>
          ))}
        </div>
      )}

      {/* Description */}
      <div className="section-header" style={{ color: ST.blue }}>
        <span>Description</span>
      </div>
      <div className="markdown-content text-sm" style={{ lineHeight: "1.75" }}>
        <ReactMarkdown>{edgeData.description}</ReactMarkdown>
      </div>
    </div>
  );
}
