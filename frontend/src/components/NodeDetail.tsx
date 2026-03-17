import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { fetchNode, fetchNeighbors } from "../api/client";
import { ST, TYPE_COLORS, TYPE_LABELS } from "../styles/theme";
import type { NodeDetail as NodeDetailType, NeighborEntry } from "../types";

interface NodeDetailProps {
  nodeId: string;
  onNodeClick: (nodeId: string) => void;
}

export default function NodeDetail({ nodeId, onNodeClick }: NodeDetailProps) {
  const [detail, setDetail] = useState<NodeDetailType | null>(null);
  const [neighbors, setNeighbors] = useState<NeighborEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchNode(nodeId), fetchNeighbors(nodeId)])
      .then(([d, n]) => {
        setDetail(d);
        setNeighbors(n.neighbors);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [nodeId]);

  if (loading) return <div className="flex justify-center py-12"><div className="spinner" /></div>;
  if (!detail) return <div className="text-center py-12" style={{ color: ST.textGrey }}>Node not found</div>;

  const color = TYPE_COLORS[detail.entity_type] || TYPE_COLORS.UNKNOWN;
  const typeLabel = TYPE_LABELS[detail.entity_type] || detail.entity_type;

  return (
    <div>
      {/* Header card */}
      <div className="p-4 rounded-xl mb-4"
        style={{
          background: `linear-gradient(135deg, ${ST.navy} 0%, ${color}15 100%)`,
          border: `1px solid ${color}33`,
        }}>
        <h2 className="text-lg font-bold mb-2" style={{ color: ST.white }}>{detail.id}</h2>
        <div className="flex gap-2 flex-wrap">
          <span className="type-badge" style={{ background: color }}>{typeLabel}</span>
          <span className="text-xs rounded-lg px-3 py-1"
            style={{ color: ST.textGrey, background: `${ST.navy}aa` }}>
            {detail.degree} connections
          </span>
        </div>
      </div>

      {/* Description */}
      <div className="section-header" style={{ color: ST.blue }}>
        <span>Description</span>
      </div>
      <div className="markdown-content text-sm mb-4" style={{ lineHeight: "1.75" }}>
        <ReactMarkdown>{detail.description}</ReactMarkdown>
      </div>

      {/* Source text */}
      {detail.source_text && (
        <>
          <div className="section-header" style={{ color: ST.success }}>
            <span>Source Text</span>
          </div>
          <div className="rounded-lg p-4 mb-4 max-h-72 overflow-y-auto detail-scroll"
            style={{ background: ST.navy, border: `1px solid ${ST.border}` }}>
            <div className="markdown-content text-xs" style={{ color: ST.lightPeach, lineHeight: "1.6" }}>
              <ReactMarkdown>{detail.source_text}</ReactMarkdown>
            </div>
          </div>
        </>
      )}

      {/* Connections */}
      {neighbors.length > 0 && (
        <>
          <div className="section-header" style={{ color: ST.orange }}>
            <span>Connections ({neighbors.length})</span>
          </div>
          {neighbors.map((n) => {
            const nColor = TYPE_COLORS[n.entity_type] || ST.textGrey;
            return (
              <div key={`${n.direction}-${n.id}`}
                className="connection-item cursor-pointer"
                style={{ borderLeftColor: nColor }}
                onClick={() => onNodeClick(n.id)}>
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: nColor }}>
                    {n.direction === "out" ? "\u2192" : "\u2190"}
                  </span>
                  <span className="font-semibold text-sm">{n.id}</span>
                  <span className="text-[9px] ml-auto opacity-60" style={{ color: nColor }}>
                    {TYPE_LABELS[n.entity_type] || n.entity_type}
                  </span>
                </div>
                {n.edge_description && (
                  <p className="text-[11px] mt-1 leading-snug" style={{ color: ST.textGrey }}>
                    {n.edge_description.slice(0, 150)}{n.edge_description.length > 150 ? "..." : ""}
                  </p>
                )}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
