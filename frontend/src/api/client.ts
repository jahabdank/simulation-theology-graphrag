import type {
  GraphResponse,
  NodeDetail,
  NeighborResponse,
  QueryResponse,
  SearchResponse,
  StatsResponse,
} from "../types";

const BASE = "/api";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export function fetchGraph(): Promise<GraphResponse> {
  return fetchJSON(`${BASE}/graph`);
}

export function fetchNode(nodeId: string): Promise<NodeDetail> {
  return fetchJSON(`${BASE}/node/${encodeURIComponent(nodeId)}`);
}

export function fetchNeighbors(nodeId: string): Promise<NeighborResponse> {
  return fetchJSON(`${BASE}/node/${encodeURIComponent(nodeId)}/neighbors`);
}

export function fetchSearch(q: string): Promise<SearchResponse> {
  return fetchJSON(`${BASE}/search?q=${encodeURIComponent(q)}`);
}

export function postQuery(question: string, mode = "hybrid"): Promise<QueryResponse> {
  return fetchJSON(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode }),
  });
}

export function fetchStats(): Promise<StatsResponse> {
  return fetchJSON(`${BASE}/stats`);
}
