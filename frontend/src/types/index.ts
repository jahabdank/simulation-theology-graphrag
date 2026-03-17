export interface GraphNode {
  id: string;
  entity_type: string;
  description: string;
  degree: number;
  size: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  description: string;
  keywords: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface NodeDetail {
  id: string;
  entity_type: string;
  description: string;
  degree: number;
  source_text: string | null;
}

export interface NeighborEntry {
  id: string;
  entity_type: string;
  direction: "out" | "in";
  edge_description: string;
  edge_keywords: string;
  edge_weight: number;
}

export interface NeighborResponse {
  node_id: string;
  neighbors: NeighborEntry[];
}

export interface QueryResponse {
  response: string;
  matched_nodes: string[];
}

export interface SearchResponse {
  query: string;
  results: string[];
}

export interface StatsResponse {
  total_nodes: number;
  total_edges: number;
  entity_type_counts: Record<string, number>;
}

export type HighlightState = {
  type: "none";
} | {
  type: "search";
  primaryNodes: Set<string>;
} | {
  type: "llm";
  primaryNodes: Set<string>;
};
