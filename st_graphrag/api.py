"""FastAPI backend serving graph data from LightRAG storage."""

import asyncio
import json
import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path

import networkx as nx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import load_config

logger = logging.getLogger(__name__)


# --- Pydantic Models ---

class GraphNode(BaseModel):
    id: str
    entity_type: str
    description: str
    degree: int
    size: float

class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    description: str
    keywords: str

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class NodeDetail(BaseModel):
    id: str
    entity_type: str
    description: str
    degree: int
    source_text: str | None = None

class NeighborEntry(BaseModel):
    id: str
    entity_type: str
    direction: str  # "out" or "in"
    edge_description: str
    edge_keywords: str
    edge_weight: float

class NeighborResponse(BaseModel):
    node_id: str
    neighbors: list[NeighborEntry]

class QueryRequest(BaseModel):
    question: str
    mode: str = "hybrid"

class QueryResponse(BaseModel):
    response: str
    matched_nodes: list[str]

class SearchResponse(BaseModel):
    query: str
    results: list[str]

class StatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    entity_type_counts: dict[str, int]


# --- App State ---

class AppState:
    G: nx.DiGraph
    text_chunks: dict
    entity_chunks: dict
    all_node_ids_lower: dict[str, str]


def _load_graph_data(working_dir: Path) -> tuple:
    G = nx.read_graphml(working_dir / "graph_chunk_entity_relation.graphml")
    text_chunks = {}
    p = working_dir / "kv_store_text_chunks.json"
    if p.exists():
        text_chunks = json.loads(p.read_text())
    entity_chunks = {}
    p = working_dir / "kv_store_entity_chunks.json"
    if p.exists():
        entity_chunks = json.loads(p.read_text())
    return G, text_chunks, entity_chunks


def _get_entity_source_text(entity_name: str, entity_chunks: dict, text_chunks: dict) -> str | None:
    for key in [entity_name, entity_name.lower(), entity_name.title()]:
        if key in entity_chunks:
            chunk_data = entity_chunks[key]
            chunk_ids = chunk_data.get("chunk_ids", [])
            texts = []
            for cid in chunk_ids[:3]:
                for tk, tv in text_chunks.items():
                    if isinstance(tv, dict) and cid in tv:
                        texts.append(tv[cid].get("content", ""))
                    elif tk == cid and isinstance(tv, dict):
                        texts.append(tv.get("content", ""))
            if texts:
                return "\n\n---\n\n".join(texts)
    return None


def _find_mentioned_nodes(text: str, node_ids_lower: dict[str, str]) -> list[str]:
    matched = set()
    text_lower = text.lower()
    for name_lower, name in node_ids_lower.items():
        if len(name_lower) > 2 and name_lower in text_lower:
            matched.add(name)
    return list(matched)


# --- App ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    working_dir = Path(config.lightrag.working_dir)
    logger.info("Loading graph data from %s", working_dir)

    G, text_chunks, entity_chunks = _load_graph_data(working_dir)
    app.state.G = G
    app.state.text_chunks = text_chunks
    app.state.entity_chunks = entity_chunks
    app.state.all_node_ids_lower = {nid.lower(): nid for nid in G.nodes()}

    logger.info("Graph loaded: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    yield
    logger.info("Shutting down")


app = FastAPI(title="ST Knowledge Graph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/graph", response_model=GraphResponse)
async def get_graph():
    G = app.state.G
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) if degrees else 1
    MIN_SIZE, MAX_SIZE = 2.0, 35.0
    log_max = math.log1p(max_deg)

    nodes = []
    for node_id, data in G.nodes(data=True):
        deg = degrees.get(node_id, 0)
        t = math.log1p(deg) / log_max if log_max > 0 else 0  # 0.0 to 1.0
        size = MIN_SIZE + (MAX_SIZE - MIN_SIZE) * t
        nodes.append(GraphNode(
            id=node_id,
            entity_type=data.get("entity_type", "UNKNOWN"),
            description=data.get("description", ""),
            degree=deg,
            size=round(size, 1),
        ))

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append(GraphEdge(
            source=u, target=v,
            weight=float(data.get("weight", 1.0)),
            description=data.get("description", ""),
            keywords=data.get("keywords", ""),
        ))

    return GraphResponse(nodes=nodes, edges=edges)


@app.get("/api/node/{node_id}", response_model=NodeDetail)
async def get_node(node_id: str):
    G = app.state.G
    if node_id not in G.nodes:
        return NodeDetail(id=node_id, entity_type="UNKNOWN", description="Node not found", degree=0)

    data = G.nodes[node_id]
    source_text = _get_entity_source_text(node_id, app.state.entity_chunks, app.state.text_chunks)

    return NodeDetail(
        id=node_id,
        entity_type=data.get("entity_type", "UNKNOWN"),
        description=data.get("description", ""),
        degree=G.degree(node_id),
        source_text=source_text,
    )


@app.get("/api/node/{node_id}/neighbors", response_model=NeighborResponse)
async def get_neighbors(node_id: str):
    G = app.state.G
    neighbors = []

    if node_id in G:
        for neighbor in G.neighbors(node_id):
            ed = G.get_edge_data(node_id, neighbor, default={})
            neighbors.append(NeighborEntry(
                id=neighbor,
                entity_type=G.nodes[neighbor].get("entity_type", "UNKNOWN") if neighbor in G.nodes else "UNKNOWN",
                direction="out",
                edge_description=ed.get("description", ""),
                edge_keywords=ed.get("keywords", ""),
                edge_weight=float(ed.get("weight", 1.0)),
            ))
        if hasattr(G, "predecessors"):
            for pred in G.predecessors(node_id):
                if pred != node_id and pred not in [n.id for n in neighbors]:
                    ed = G.get_edge_data(pred, node_id, default={})
                    neighbors.append(NeighborEntry(
                        id=pred,
                        entity_type=G.nodes[pred].get("entity_type", "UNKNOWN") if pred in G.nodes else "UNKNOWN",
                        direction="in",
                        edge_description=ed.get("description", ""),
                        edge_keywords=ed.get("keywords", ""),
                        edge_weight=float(ed.get("weight", 1.0)),
                    ))

    return NeighborResponse(node_id=node_id, neighbors=neighbors)


@app.get("/api/search", response_model=SearchResponse)
async def search_nodes(q: str = Query(..., min_length=1)):
    G = app.state.G
    q_lower = q.lower()
    results = []
    for node_id, data in G.nodes(data=True):
        if (q_lower in node_id.lower()
                or q_lower in data.get("description", "").lower()):
            results.append(node_id)
    return SearchResponse(query=q, results=results)


@app.post("/api/query", response_model=QueryResponse)
async def llm_query(req: QueryRequest):
    from .client import STGraphRAGClient
    client = STGraphRAGClient()
    await client.initialize()
    try:
        result = await client.query(req.question, mode=req.mode)
    finally:
        await client.finalize()

    matched = _find_mentioned_nodes(result, app.state.all_node_ids_lower)
    return QueryResponse(response=result, matched_nodes=matched)


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    G = app.state.G
    type_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        t = data.get("entity_type", "UNKNOWN")
        type_counts[t] = type_counts.get(t, 0) + 1
    return StatsResponse(
        total_nodes=G.number_of_nodes(),
        total_edges=G.number_of_edges(),
        entity_type_counts=type_counts,
    )
