"""Interactive Knowledge Graph Visualizer using Dash + Cytoscape."""

import json
import math
import logging
from pathlib import Path

import dash_cytoscape as cyto
import networkx as nx
from dash import Dash, DiskcacheManager, Input, Output, State, callback_context, dcc, html, no_update

from .config import load_config

logger = logging.getLogger(__name__)

# Load extra layout algorithms (dagre, cola, klay, etc.)
cyto.load_extra_layouts()

# Entity type → color mapping
TYPE_COLORS = {
    "axiom": "#e94560",
    "entity": "#f5a623",
    "concept": "#4a9eff",
    "architectural_component": "#53d8fb",
    "biblical_figure": "#2ecc71",
    "religious_concept": "#9b59b6",
    "st_term": "#1abc9c",
    "scripture_mapping": "#95a5a6",
    "UNKNOWN": "#6c757d",
}

LAYOUT_OPTIONS = [
    {"label": "Force-directed (cose)", "value": "cose"},
    {"label": "Cola (constraint-based)", "value": "cola"},
    {"label": "Dagre (hierarchical)", "value": "dagre"},
    {"label": "Circular", "value": "circle"},
    {"label": "Concentric", "value": "concentric"},
    {"label": "Grid", "value": "grid"},
]


def _load_graph_data(working_dir: Path):
    """Load all graph data from LightRAG storage."""
    graphml_path = working_dir / "graph_chunk_entity_relation.graphml"
    G = nx.read_graphml(graphml_path)

    text_chunks = {}
    chunks_path = working_dir / "kv_store_text_chunks.json"
    if chunks_path.exists():
        text_chunks = json.loads(chunks_path.read_text())

    entity_chunks = {}
    ec_path = working_dir / "kv_store_entity_chunks.json"
    if ec_path.exists():
        entity_chunks = json.loads(ec_path.read_text())

    return G, text_chunks, entity_chunks


def _build_cytoscape_elements(G: nx.Graph):
    """Convert NetworkX graph to Cytoscape elements format."""
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) if degrees else 1

    elements = []

    for node_id, data in G.nodes(data=True):
        deg = degrees.get(node_id, 0)
        size = 15 + math.log1p(deg) * 12
        etype = data.get("entity_type", "UNKNOWN")
        color = TYPE_COLORS.get(etype, TYPE_COLORS["UNKNOWN"])

        elements.append({
            "data": {
                "id": node_id,
                "label": node_id,
                "entity_type": etype,
                "description": data.get("description", ""),
                "source_id": data.get("source_id", ""),
                "degree": deg,
                "size": size,
                "color": color,
            }
        })

    for u, v, data in G.edges(data=True):
        weight = float(data.get("weight", 1.0))
        elements.append({
            "data": {
                "source": u,
                "target": v,
                "weight": weight,
                "description": data.get("description", ""),
                "keywords": data.get("keywords", ""),
                "edge_width": max(0.5, min(weight, 5.0)),
            }
        })

    return elements


def _get_entity_source_text(entity_name, entity_chunks, text_chunks):
    """Get the original source text for an entity from chunk storage."""
    ec_key = entity_name
    # Try case variations
    for key in [ec_key, ec_key.lower(), ec_key.title()]:
        if key in entity_chunks:
            chunk_data = entity_chunks[key]
            chunk_ids = chunk_data.get("chunk_ids", [])
            texts = []
            for cid in chunk_ids[:3]:  # limit to 3 chunks
                for tk, tv in text_chunks.items():
                    if isinstance(tv, dict) and cid in str(tv):
                        # text_chunks has nested structure
                        if cid in tv:
                            texts.append(tv[cid].get("content", ""))
                    elif tk == cid:
                        texts.append(tv.get("content", ""))
            if texts:
                return "\n\n---\n\n".join(texts)
    return None


def _build_stylesheet():
    """Build the Cytoscape CSS stylesheet."""
    return [
        # Default node style
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": "data(size)",
                "height": "data(size)",
                "background-color": "data(color)",
                "color": "#ffffff",
                "font-size": "10px",
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": "5px",
                "text-outline-color": "#1a1a2e",
                "text-outline-width": "2px",
                "border-width": "1px",
                "border-color": "#333",
            },
        },
        # Default edge style
        {
            "selector": "edge",
            "style": {
                "width": "data(edge_width)",
                "line-color": "#444466",
                "target-arrow-color": "#444466",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "opacity": 0.4,
            },
        },
        # Selected node
        {
            "selector": "node:selected",
            "style": {
                "border-width": "3px",
                "border-color": "#ffffff",
                "background-color": "#ff6b6b",
                "font-size": "14px",
                "font-weight": "bold",
                "z-index": 9999,
            },
        },
        # Selected edge
        {
            "selector": "edge:selected",
            "style": {
                "line-color": "#ff6b6b",
                "target-arrow-color": "#ff6b6b",
                "opacity": 1.0,
                "width": 3,
            },
        },
        # Search-highlighted nodes
        {
            "selector": ".highlighted",
            "style": {
                "border-width": "3px",
                "border-color": "#ffff00",
                "background-color": "#ffcc00",
                "font-size": "13px",
                "z-index": 9998,
            },
        },
        # Dimmed (non-matching) nodes
        {
            "selector": ".dimmed",
            "style": {
                "opacity": 0.15,
            },
        },
        # Hidden nodes (filtered out)
        {
            "selector": ".hidden",
            "style": {
                "display": "none",
            },
        },
    ]


def create_app(config=None):
    """Create and configure the Dash app."""
    if config is None:
        config = load_config()

    working_dir = Path(config.lightrag.working_dir)
    G, text_chunks, entity_chunks = _load_graph_data(working_dir)
    elements = _build_cytoscape_elements(G)
    degrees = dict(G.degree())

    # Get all entity types for filter
    entity_types = sorted(set(
        data.get("entity_type", "UNKNOWN")
        for _, data in G.nodes(data=True)
    ))

    type_filter_options = [{"label": "All types", "value": "all"}] + [
        {"label": f"{t} ({sum(1 for _, d in G.nodes(data=True) if d.get('entity_type') == t)})",
         "value": t}
        for t in entity_types
    ]

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    # Background callback manager for long-running LLM queries
    import diskcache
    cache = diskcache.Cache(str(working_dir / ".dash_cache"))
    background_callback_manager = DiskcacheManager(cache)

    app = Dash(__name__, background_callback_manager=background_callback_manager)

    app.layout = html.Div(
        style={
            "fontFamily": "'Segoe UI', system-ui, -apple-system, sans-serif",
            "backgroundColor": "#0f0f1a",
            "color": "#e0e0e0",
            "height": "100vh",
            "display": "flex",
            "flexDirection": "column",
            "overflow": "hidden",
        },
        children=[
            # Header bar
            html.Div(
                style={
                    "padding": "8px 16px",
                    "backgroundColor": "#1a1a2e",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                    "borderBottom": "1px solid #333",
                    "flexShrink": "0",
                },
                children=[
                    html.H3(
                        "Simulation Theology Knowledge Graph",
                        style={"margin": "0", "color": "#e94560", "whiteSpace": "nowrap"},
                    ),
                    dcc.Dropdown(
                        id="layout-select",
                        options=LAYOUT_OPTIONS,
                        value="cose",
                        style={"width": "220px", "color": "#000"},
                        clearable=False,
                    ),
                    dcc.Dropdown(
                        id="type-filter",
                        options=type_filter_options,
                        value="all",
                        style={"width": "250px", "color": "#000"},
                        clearable=False,
                    ),
                    html.Span(
                        id="stats",
                        children=f"Nodes: {total_nodes} | Edges: {total_edges}",
                        style={"color": "#888", "fontSize": "13px"},
                    ),
                ],
            ),
            # Main content
            html.Div(
                style={"display": "flex", "flex": "1", "overflow": "hidden"},
                children=[
                    # Left panel
                    html.Div(
                        style={
                            "width": "400px",
                            "minWidth": "350px",
                            "backgroundColor": "#16162a",
                            "borderRight": "1px solid #333",
                            "display": "flex",
                            "flexDirection": "column",
                            "overflow": "hidden",
                        },
                        children=[
                            # Search section
                            html.Div(
                                style={
                                    "padding": "12px",
                                    "borderBottom": "1px solid #333",
                                    "flexShrink": "0",
                                },
                                children=[
                                    dcc.Input(
                                        id="search-input",
                                        type="text",
                                        placeholder="Search nodes...",
                                        debounce=True,
                                        style={
                                            "width": "100%",
                                            "padding": "8px 12px",
                                            "backgroundColor": "#1a1a2e",
                                            "border": "1px solid #444",
                                            "borderRadius": "4px",
                                            "color": "#e0e0e0",
                                            "fontSize": "14px",
                                            "marginBottom": "8px",
                                            "boxSizing": "border-box",
                                        },
                                    ),
                                    html.Div(
                                        style={"display": "flex", "gap": "8px"},
                                        children=[
                                            html.Button(
                                                "Search",
                                                id="search-btn",
                                                style={
                                                    "flex": "1",
                                                    "padding": "8px",
                                                    "backgroundColor": "#4a9eff",
                                                    "color": "white",
                                                    "border": "none",
                                                    "borderRadius": "4px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            html.Button(
                                                "Ask LLM",
                                                id="llm-query-btn",
                                                style={
                                                    "flex": "1",
                                                    "padding": "8px",
                                                    "backgroundColor": "#e94560",
                                                    "color": "white",
                                                    "border": "none",
                                                    "borderRadius": "4px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            html.Button(
                                                "Clear",
                                                id="clear-btn",
                                                style={
                                                    "padding": "8px 12px",
                                                    "backgroundColor": "#333",
                                                    "color": "white",
                                                    "border": "none",
                                                    "borderRadius": "4px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            # Detail content (scrollable)
                            html.Div(
                                id="detail-panel",
                                style={
                                    "flex": "1",
                                    "overflowY": "auto",
                                    "padding": "16px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "color": "#666",
                                            "textAlign": "center",
                                            "marginTop": "40px",
                                        },
                                        children="Click a node or edge to see details",
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Graph area
                    html.Div(
                        style={"flex": "1", "position": "relative"},
                        children=[
                            cyto.Cytoscape(
                                id="graph",
                                elements=elements,
                                layout={"name": "cose", "animate": False, "randomize": True},
                                style={"width": "100%", "height": "100%"},
                                stylesheet=_build_stylesheet(),
                                minZoom=0.1,
                                maxZoom=5.0,
                            ),
                            # Legend overlay
                            html.Div(
                                style={
                                    "position": "absolute",
                                    "bottom": "12px",
                                    "right": "12px",
                                    "backgroundColor": "rgba(26, 26, 46, 0.9)",
                                    "padding": "8px 12px",
                                    "borderRadius": "6px",
                                    "border": "1px solid #333",
                                    "fontSize": "11px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "gap": "6px",
                                            "marginBottom": "3px",
                                        },
                                        children=[
                                            html.Span(
                                                style={
                                                    "width": "10px",
                                                    "height": "10px",
                                                    "borderRadius": "50%",
                                                    "backgroundColor": color,
                                                    "display": "inline-block",
                                                },
                                            ),
                                            html.Span(etype),
                                        ],
                                    )
                                    for etype, color in TYPE_COLORS.items()
                                    if etype != "UNKNOWN"
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # Hidden store for LLM loading state
            dcc.Store(id="llm-loading-state", data=False),
        ],
    )

    # --- Callbacks ---

    @app.callback(
        Output("detail-panel", "children"),
        Input("graph", "tapNodeData"),
        Input("graph", "tapEdgeData"),
        prevent_initial_call=True,
    )
    def display_detail(node_data, edge_data):
        """Show detail panel when a node or edge is clicked."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        trigger = ctx.triggered[0]["prop_id"]

        if "tapNodeData" in trigger and node_data:
            return _render_node_detail(node_data, G, entity_chunks, text_chunks)
        elif "tapEdgeData" in trigger and edge_data:
            return _render_edge_detail(edge_data)

        return no_update

    @app.callback(
        Output("graph", "stylesheet"),
        Input("search-btn", "n_clicks"),
        Input("clear-btn", "n_clicks"),
        State("search-input", "value"),
        prevent_initial_call=True,
    )
    def handle_search(search_clicks, clear_clicks, search_text):
        """Highlight matching nodes on search, or clear highlights."""
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        trigger = ctx.triggered[0]["prop_id"]

        if "clear-btn" in trigger:
            return _build_stylesheet()

        if not search_text or not search_text.strip():
            return _build_stylesheet()

        search_lower = search_text.lower()
        matching_ids = set()
        for node_id, data in G.nodes(data=True):
            if (search_lower in node_id.lower()
                    or search_lower in data.get("description", "").lower()):
                matching_ids.add(node_id)

        if not matching_ids:
            return _build_stylesheet()

        # Add highlight/dim classes via stylesheet
        stylesheet = _build_stylesheet()
        # Dim all non-matching nodes
        stylesheet.append({
            "selector": "node",
            "style": {"opacity": 0.15, "font-size": "8px"},
        })
        # Highlight matching nodes
        for nid in matching_ids:
            stylesheet.append({
                "selector": f'node[id = "{nid}"]',
                "style": {
                    "opacity": 1.0,
                    "border-width": "3px",
                    "border-color": "#ffff00",
                    "font-size": "13px",
                    "z-index": 9998,
                },
            })
        # Keep edges to matching nodes visible
        stylesheet.append({
            "selector": "edge",
            "style": {"opacity": 0.05},
        })

        return stylesheet

    @app.callback(
        Output("detail-panel", "children", allow_duplicate=True),
        Input("llm-query-btn", "n_clicks"),
        State("search-input", "value"),
        prevent_initial_call=True,
        running=[
            (Output("llm-query-btn", "disabled"), True, False),
            (Output("llm-query-btn", "children"), "Querying...", "Ask LLM"),
            (Output("llm-query-btn", "style"), {
                "flex": "1", "padding": "8px",
                "backgroundColor": "#666", "color": "white",
                "border": "none", "borderRadius": "4px",
                "cursor": "wait",
            }, {
                "flex": "1", "padding": "8px",
                "backgroundColor": "#e94560", "color": "white",
                "border": "none", "borderRadius": "4px",
                "cursor": "pointer",
            }),
        ],
        background=True,
        manager=background_callback_manager,
    )
    def handle_llm_query(n_clicks, query_text):
        """Run an LLM query against the knowledge graph (background thread)."""
        if not query_text or not query_text.strip():
            return html.Div(
                "Enter a question in the search box first.",
                style={"color": "#e94560", "padding": "12px"},
            )

        # Show loading state immediately
        loading_header = [
            html.H4(
                "LLM Query Result",
                style={"color": "#e94560", "marginBottom": "8px"},
            ),
            html.Div(
                f'Query: "{query_text}"',
                style={
                    "color": "#888",
                    "fontSize": "12px",
                    "marginBottom": "12px",
                    "fontStyle": "italic",
                },
            ),
        ]

        try:
            import asyncio
            from .client import STGraphRAGClient

            client = STGraphRAGClient()

            # Run async query in a new event loop (safe from background thread)
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client.initialize())
                result = loop.run_until_complete(
                    client.query(query_text, mode="hybrid")
                )
            finally:
                loop.run_until_complete(client.finalize())
                loop.close()

            return html.Div(loading_header + [
                html.Hr(style={"borderColor": "#333"}),
                dcc.Markdown(
                    result,
                    style={
                        "lineHeight": "1.6",
                        "fontSize": "14px",
                    },
                ),
            ])
        except Exception as e:
            logger.error("LLM query failed: %s", e, exc_info=True)
            return html.Div(loading_header + [
                html.Hr(style={"borderColor": "#333"}),
                html.Div(
                    f"Query failed: {e}",
                    style={"color": "#e94560", "padding": "12px"},
                ),
            ])

    @app.callback(
        Output("graph", "layout"),
        Input("layout-select", "value"),
    )
    def update_layout(layout_name):
        """Change the graph layout algorithm."""
        return {"name": layout_name, "animate": True}

    @app.callback(
        Output("graph", "elements"),
        Input("type-filter", "value"),
    )
    def filter_by_type(selected_type):
        """Filter nodes by entity type."""
        if selected_type == "all":
            return elements

        filtered_node_ids = set()
        filtered = []
        for el in elements:
            data = el["data"]
            if "source" not in data:  # node
                if data.get("entity_type") == selected_type:
                    filtered.append(el)
                    filtered_node_ids.add(data["id"])

        # Include edges where both endpoints are visible
        for el in elements:
            data = el["data"]
            if "source" in data:  # edge
                if data["source"] in filtered_node_ids and data["target"] in filtered_node_ids:
                    filtered.append(el)

        return filtered

    return app


def _render_node_detail(node_data, G, entity_chunks, text_chunks):
    """Render the detail panel for a clicked node."""
    node_id = node_data["id"]
    etype = node_data.get("entity_type", "UNKNOWN")
    description = node_data.get("description", "No description available.")
    degree = node_data.get("degree", 0)
    color = TYPE_COLORS.get(etype, TYPE_COLORS["UNKNOWN"])

    # Get connections
    neighbors = []
    if node_id in G:
        for neighbor in G.neighbors(node_id):
            edge_data = G.get_edge_data(node_id, neighbor, default={})
            edge_desc = edge_data.get("description", "")[:120]
            neighbors.append((neighbor, edge_desc))
        # Also get predecessors (for directed graphs)
        if hasattr(G, "predecessors"):
            for pred in G.predecessors(node_id):
                if pred != node_id and pred not in [n for n, _ in neighbors]:
                    edge_data = G.get_edge_data(pred, node_id, default={})
                    edge_desc = edge_data.get("description", "")[:120]
                    neighbors.append((pred, f"(incoming) {edge_desc}"))

    neighbors.sort(key=lambda x: x[0])

    # Get source text from chunks
    source_text = _get_entity_source_text(node_id, entity_chunks, text_chunks)

    children = [
        # Header
        html.H3(node_id, style={"margin": "0 0 4px 0", "color": "#fff"}),
        html.Div(
            style={"display": "flex", "gap": "8px", "marginBottom": "12px"},
            children=[
                html.Span(
                    etype,
                    style={
                        "backgroundColor": color,
                        "color": "white",
                        "padding": "2px 10px",
                        "borderRadius": "12px",
                        "fontSize": "12px",
                        "fontWeight": "bold",
                    },
                ),
                html.Span(
                    f"{degree} connections",
                    style={"color": "#888", "fontSize": "12px", "lineHeight": "24px"},
                ),
            ],
        ),
        # Description
        html.H4("Description", style={"color": "#4a9eff", "marginBottom": "4px"}),
        dcc.Markdown(
            description,
            style={"lineHeight": "1.6", "fontSize": "13px", "marginBottom": "16px"},
        ),
    ]

    # Source text section
    if source_text:
        children.extend([
            html.Hr(style={"borderColor": "#333"}),
            html.H4("Source Text", style={"color": "#2ecc71", "marginBottom": "4px"}),
            dcc.Markdown(
                source_text,
                style={"lineHeight": "1.5", "fontSize": "12px", "color": "#bbb"},
            ),
        ])

    # Connections section
    if neighbors:
        children.extend([
            html.Hr(style={"borderColor": "#333"}),
            html.H4(
                f"Connections ({len(neighbors)})",
                style={"color": "#f5a623", "marginBottom": "8px"},
            ),
        ])
        for neighbor_name, edge_desc in neighbors:
            n_type = G.nodes[neighbor_name].get("entity_type", "") if neighbor_name in G.nodes else ""
            n_color = TYPE_COLORS.get(n_type, "#666")
            children.append(
                html.Div(
                    style={
                        "padding": "6px 8px",
                        "marginBottom": "4px",
                        "backgroundColor": "#1a1a2e",
                        "borderRadius": "4px",
                        "borderLeft": f"3px solid {n_color}",
                    },
                    children=[
                        html.Span(
                            neighbor_name,
                            style={"fontWeight": "bold", "fontSize": "13px"},
                        ),
                        html.Div(
                            edge_desc,
                            style={"fontSize": "11px", "color": "#888", "marginTop": "2px"},
                        ) if edge_desc else None,
                    ],
                )
            )

    return children


def _render_edge_detail(edge_data):
    """Render the detail panel for a clicked edge."""
    source = edge_data.get("source", "?")
    target = edge_data.get("target", "?")
    description = edge_data.get("description", "No description available.")
    keywords = edge_data.get("keywords", "")
    weight = edge_data.get("weight", 1.0)

    keyword_badges = []
    if keywords:
        for kw in keywords.split(","):
            kw = kw.strip()
            if kw:
                keyword_badges.append(
                    html.Span(
                        kw,
                        style={
                            "backgroundColor": "#333",
                            "padding": "2px 8px",
                            "borderRadius": "10px",
                            "fontSize": "11px",
                            "marginRight": "4px",
                            "marginBottom": "4px",
                            "display": "inline-block",
                        },
                    )
                )

    return [
        html.H3("Relationship", style={"margin": "0 0 8px 0", "color": "#fff"}),
        html.Div(
            style={
                "padding": "12px",
                "backgroundColor": "#1a1a2e",
                "borderRadius": "6px",
                "marginBottom": "12px",
            },
            children=[
                html.Span(source, style={"color": "#4a9eff", "fontWeight": "bold"}),
                html.Span(" → ", style={"color": "#666", "margin": "0 8px"}),
                html.Span(target, style={"color": "#f5a623", "fontWeight": "bold"}),
            ],
        ),
        html.Div(
            f"Weight: {weight:.1f}",
            style={"color": "#888", "fontSize": "12px", "marginBottom": "12px"},
        ),
        # Keywords
        html.Div(
            keyword_badges,
            style={"marginBottom": "16px"},
        ) if keyword_badges else None,
        # Description
        html.H4("Description", style={"color": "#4a9eff", "marginBottom": "4px"}),
        dcc.Markdown(
            description,
            style={"lineHeight": "1.6", "fontSize": "13px"},
        ),
    ]
