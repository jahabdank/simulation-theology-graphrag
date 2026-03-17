import { useEffect, useState } from "react";
import Graph from "graphology";
import { fetchGraph } from "../api/client";
import { TYPE_COLORS } from "../styles/theme";
import type { StatsResponse } from "../types";
import { fetchStats } from "../api/client";

export function useGraph() {
  const [graph, setGraph] = useState<Graph | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [data, statsData] = await Promise.all([fetchGraph(), fetchStats()]);
        if (cancelled) return;

        const g = new Graph({ type: "directed", multi: false });

        for (const node of data.nodes) {
          const color = TYPE_COLORS[node.entity_type] || TYPE_COLORS.UNKNOWN;
          g.addNode(node.id, {
            label: node.id,
            size: node.size,
            color,
            x: Math.random() * 1000,
            y: Math.random() * 1000,
            entity_type: node.entity_type,
            description: node.description,
            degree: node.degree,
          });
        }

        for (const edge of data.edges) {
          if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
            try {
              g.addEdge(edge.source, edge.target, {
                weight: edge.weight,
                size: Math.max(0.5, Math.min(edge.weight, 4)),
                color: "#2A2D4A",
                description: edge.description,
                keywords: edge.keywords,
              });
            } catch {
              // skip duplicate edges
            }
          }
        }

        setGraph(g);
        setStats(statsData);
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load graph");
          setLoading(false);
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return { graph, stats, loading, error };
}
