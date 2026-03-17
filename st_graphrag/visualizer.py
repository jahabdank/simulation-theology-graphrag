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

# --- Brand Palette ---
BRAND = {
    # Primary
    "blue": "#6B8CFF",
    "coral": "#F07050",
    "orange": "#F28C50",
    "peach": "#F9B870",
    "light_peach": "#F5C4A0",
    # Backgrounds
    "navy": "#181A2E",
    "navy_light": "#1E2040",
    "cream": "#FAF5F0",
    "white": "#FFFFFF",
    # Text
    "text_dark": "#1A1A2E",
    "text_grey": "#6B7280",
    "text_light": "#E5E7EB",
    # Status
    "success": "#10B981",
    "warning": "#FFD700",
    "warning_orange": "#F28C50",
    "error": "#FF4444",
    # Other
    "inactive": "#555555",
    "font": "'Open Sans', 'Segoe UI', system-ui, -apple-system, sans-serif",
}

# Entity type → color mapping (using brand palette)
TYPE_COLORS = {
    "axiom": BRAND["coral"],           # F07050
    "entity": BRAND["orange"],          # F28C50
    "concept": BRAND["blue"],           # 6B8CFF
    "architectural_component": "#8B9FFF",  # COPY shade
    "biblical_figure": BRAND["success"],   # 10B981
    "religious_concept": "#9B59B6",
    "st_term": BRAND["peach"],          # F9B870
    "scripture_mapping": "#9CA3AF",     # Source Files zone
    "UNKNOWN": BRAND["text_grey"],      # 6B7280
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
    for key in [entity_name, entity_name.lower(), entity_name.title()]:
        if key in entity_chunks:
            chunk_data = entity_chunks[key]
            chunk_ids = chunk_data.get("chunk_ids", [])
            texts = []
            for cid in chunk_ids[:3]:
                for tk, tv in text_chunks.items():
                    if isinstance(tv, dict) and cid in str(tv):
                        if cid in tv:
                            texts.append(tv[cid].get("content", ""))
                    elif tk == cid:
                        texts.append(tv.get("content", ""))
            if texts:
                return "\n\n---\n\n".join(texts)
    return None


def _build_stylesheet():
    """Build the Cytoscape CSS stylesheet with brand colors."""
    return [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": "data(size)",
                "height": "data(size)",
                "background-color": "data(color)",
                "color": BRAND["text_light"],
                "font-size": "10px",
                "font-family": BRAND["font"],
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": "5px",
                "text-outline-color": BRAND["navy"],
                "text-outline-width": "2px",
                "border-width": "1px",
                "border-color": BRAND["navy_light"],
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": "data(edge_width)",
                "line-color": "#2A2D4A",
                "target-arrow-color": "#2A2D4A",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "opacity": 0.35,
            },
        },
        {
            "selector": "node:selected",
            "style": {
                "border-width": "3px",
                "border-color": BRAND["white"],
                "background-color": BRAND["coral"],
                "font-size": "14px",
                "font-weight": "bold",
                "z-index": 9999,
            },
        },
        {
            "selector": "edge:selected",
            "style": {
                "line-color": BRAND["coral"],
                "target-arrow-color": BRAND["coral"],
                "opacity": 1.0,
                "width": 3,
            },
        },
        {
            "selector": ".highlighted",
            "style": {
                "border-width": "3px",
                "border-color": BRAND["warning"],
                "font-size": "13px",
                "z-index": 9998,
            },
        },
        {
            "selector": ".dimmed",
            "style": {"opacity": 0.15},
        },
        {
            "selector": ".hidden",
            "style": {"display": "none"},
        },
    ]


# --- Reusable style dicts ---

_BUTTON_SEARCH = {
    "flex": "1", "padding": "8px",
    "backgroundColor": BRAND["blue"], "color": BRAND["white"],
    "border": "none", "borderRadius": "4px", "cursor": "pointer",
    "fontFamily": BRAND["font"], "fontWeight": "600",
}

_BUTTON_LLM = {
    "flex": "1", "padding": "8px",
    "backgroundColor": BRAND["coral"], "color": BRAND["white"],
    "border": "none", "borderRadius": "4px", "cursor": "pointer",
    "fontFamily": BRAND["font"], "fontWeight": "600",
}

_BUTTON_LLM_LOADING = {
    "flex": "1", "padding": "8px",
    "backgroundColor": BRAND["inactive"], "color": BRAND["text_light"],
    "border": "none", "borderRadius": "4px", "cursor": "wait",
    "fontFamily": BRAND["font"], "fontWeight": "600",
}

_BUTTON_CLEAR = {
    "padding": "8px 12px",
    "backgroundColor": BRAND["navy_light"], "color": BRAND["text_light"],
    "border": f"1px solid {BRAND['text_grey']}", "borderRadius": "4px",
    "cursor": "pointer", "fontFamily": BRAND["font"],
}


def create_app(config=None):
    """Create and configure the Dash app."""
    if config is None:
        config = load_config()

    working_dir = Path(config.lightrag.working_dir)
    G, text_chunks, entity_chunks = _load_graph_data(working_dir)
    elements = _build_cytoscape_elements(G)

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

    import diskcache
    cache = diskcache.Cache(str(working_dir / ".dash_cache"))
    background_callback_manager = DiskcacheManager(cache)

    app = Dash(__name__, background_callback_manager=background_callback_manager)

    app.layout = html.Div(
        style={
            "fontFamily": BRAND["font"],
            "backgroundColor": BRAND["navy"],
            "color": BRAND["text_light"],
            "height": "100vh",
            "display": "flex",
            "flexDirection": "column",
            "overflow": "hidden",
        },
        children=[
            # Header bar
            html.Div(
                style={
                    "padding": "10px 20px",
                    "background": f"linear-gradient(135deg, {BRAND['navy']}, {BRAND['navy_light']})",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "16px",
                    "borderBottom": f"2px solid {BRAND['blue']}",
                    "flexShrink": "0",
                },
                children=[
                    html.H3(
                        "Simulation Theology Knowledge Graph",
                        style={
                            "margin": "0",
                            "color": BRAND["blue"],
                            "whiteSpace": "nowrap",
                            "fontWeight": "700",
                            "letterSpacing": "0.5px",
                        },
                    ),
                    dcc.Dropdown(
                        id="layout-select",
                        options=LAYOUT_OPTIONS,
                        value="cose",
                        style={"width": "220px", "color": BRAND["text_dark"]},
                        clearable=False,
                    ),
                    dcc.Dropdown(
                        id="type-filter",
                        options=type_filter_options,
                        value="all",
                        style={"width": "250px", "color": BRAND["text_dark"]},
                        clearable=False,
                    ),
                    html.Span(
                        id="stats",
                        children=f"Nodes: {total_nodes}  |  Edges: {total_edges}",
                        style={"color": BRAND["text_grey"], "fontSize": "13px"},
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
                            "width": "420px",
                            "minWidth": "360px",
                            "backgroundColor": BRAND["navy_light"],
                            "borderRight": f"1px solid #2A2D4A",
                            "display": "flex",
                            "flexDirection": "column",
                            "overflow": "hidden",
                        },
                        children=[
                            # Search section
                            html.Div(
                                style={
                                    "padding": "14px",
                                    "borderBottom": f"1px solid #2A2D4A",
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
                                            "padding": "10px 14px",
                                            "backgroundColor": BRAND["navy"],
                                            "border": f"1px solid #2A2D4A",
                                            "borderRadius": "6px",
                                            "color": BRAND["text_light"],
                                            "fontSize": "14px",
                                            "fontFamily": BRAND["font"],
                                            "marginBottom": "10px",
                                            "boxSizing": "border-box",
                                        },
                                    ),
                                    html.Div(
                                        style={"display": "flex", "gap": "8px"},
                                        children=[
                                            html.Button("Search", id="search-btn", style=_BUTTON_SEARCH),
                                            html.Button("Ask LLM", id="llm-query-btn", style=_BUTTON_LLM),
                                            html.Button("Clear", id="clear-btn", style=_BUTTON_CLEAR),
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
                                            "color": BRAND["text_grey"],
                                            "textAlign": "center",
                                            "marginTop": "60px",
                                            "fontSize": "14px",
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
                                    "backgroundColor": f"rgba(24, 26, 46, 0.92)",
                                    "padding": "10px 14px",
                                    "borderRadius": "8px",
                                    "border": f"1px solid #2A2D4A",
                                    "fontSize": "11px",
                                    "fontFamily": BRAND["font"],
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "gap": "6px",
                                            "marginBottom": "4px",
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
                                            html.Span(
                                                etype,
                                                style={"color": BRAND["text_light"]},
                                            ),
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

        stylesheet = _build_stylesheet()
        stylesheet.append({
            "selector": "node",
            "style": {"opacity": 0.12, "font-size": "8px"},
        })
        for nid in matching_ids:
            stylesheet.append({
                "selector": f'node[id = "{nid}"]',
                "style": {
                    "opacity": 1.0,
                    "border-width": "3px",
                    "border-color": BRAND["warning"],
                    "font-size": "13px",
                    "z-index": 9998,
                },
            })
        stylesheet.append({
            "selector": "edge",
            "style": {"opacity": 0.04},
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
            (Output("llm-query-btn", "style"), _BUTTON_LLM_LOADING, _BUTTON_LLM),
        ],
        background=True,
        manager=background_callback_manager,
    )
    def handle_llm_query(n_clicks, query_text):
        if not query_text or not query_text.strip():
            return html.Div(
                "Enter a question in the search box first.",
                style={"color": BRAND["error"], "padding": "12px"},
            )

        header = [
            html.H4("LLM Query Result", style={"color": BRAND["coral"], "marginBottom": "8px"}),
            html.Div(
                f'Query: "{query_text}"',
                style={
                    "color": BRAND["text_grey"], "fontSize": "12px",
                    "marginBottom": "12px", "fontStyle": "italic",
                },
            ),
        ]

        try:
            import asyncio
            from .client import STGraphRAGClient
            client = STGraphRAGClient()
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(client.initialize())
                result = loop.run_until_complete(client.query(query_text, mode="hybrid"))
            finally:
                loop.run_until_complete(client.finalize())
                loop.close()

            return html.Div(header + [
                html.Hr(style={"borderColor": "#2A2D4A"}),
                dcc.Markdown(result, style={"lineHeight": "1.6", "fontSize": "14px"}),
            ])
        except Exception as e:
            logger.error("LLM query failed: %s", e, exc_info=True)
            return html.Div(header + [
                html.Hr(style={"borderColor": "#2A2D4A"}),
                html.Div(f"Query failed: {e}", style={"color": BRAND["error"], "padding": "12px"}),
            ])

    @app.callback(
        Output("graph", "layout"),
        Input("layout-select", "value"),
    )
    def update_layout(layout_name):
        return {"name": layout_name, "animate": True}

    @app.callback(
        Output("graph", "elements"),
        Input("type-filter", "value"),
    )
    def filter_by_type(selected_type):
        if selected_type == "all":
            return elements
        filtered_node_ids = set()
        filtered = []
        for el in elements:
            data = el["data"]
            if "source" not in data:
                if data.get("entity_type") == selected_type:
                    filtered.append(el)
                    filtered_node_ids.add(data["id"])
        for el in elements:
            data = el["data"]
            if "source" in data:
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

    neighbors = []
    if node_id in G:
        for neighbor in G.neighbors(node_id):
            edge_data = G.get_edge_data(node_id, neighbor, default={})
            edge_desc = edge_data.get("description", "")[:120]
            neighbors.append((neighbor, edge_desc))
        if hasattr(G, "predecessors"):
            for pred in G.predecessors(node_id):
                if pred != node_id and pred not in [n for n, _ in neighbors]:
                    edge_data = G.get_edge_data(pred, node_id, default={})
                    edge_desc = edge_data.get("description", "")[:120]
                    neighbors.append((pred, f"(incoming) {edge_desc}"))
    neighbors.sort(key=lambda x: x[0])

    source_text = _get_entity_source_text(node_id, entity_chunks, text_chunks)

    children = [
        html.H3(node_id, style={"margin": "0 0 6px 0", "color": BRAND["white"]}),
        html.Div(
            style={"display": "flex", "gap": "8px", "marginBottom": "14px"},
            children=[
                html.Span(
                    etype,
                    style={
                        "backgroundColor": color, "color": BRAND["white"],
                        "padding": "3px 12px", "borderRadius": "12px",
                        "fontSize": "12px", "fontWeight": "600",
                    },
                ),
                html.Span(
                    f"{degree} connections",
                    style={"color": BRAND["text_grey"], "fontSize": "12px", "lineHeight": "24px"},
                ),
            ],
        ),
        html.H4("Description", style={"color": BRAND["blue"], "marginBottom": "6px", "fontSize": "14px"}),
        dcc.Markdown(
            description,
            style={"lineHeight": "1.7", "fontSize": "13px", "marginBottom": "16px"},
        ),
    ]

    if source_text:
        children.extend([
            html.Hr(style={"borderColor": "#2A2D4A", "margin": "16px 0"}),
            html.H4("Source Text", style={"color": BRAND["success"], "marginBottom": "6px", "fontSize": "14px"}),
            dcc.Markdown(
                source_text,
                style={"lineHeight": "1.6", "fontSize": "12px", "color": BRAND["light_peach"]},
            ),
        ])

    if neighbors:
        children.extend([
            html.Hr(style={"borderColor": "#2A2D4A", "margin": "16px 0"}),
            html.H4(
                f"Connections ({len(neighbors)})",
                style={"color": BRAND["orange"], "marginBottom": "10px", "fontSize": "14px"},
            ),
        ])
        for neighbor_name, edge_desc in neighbors:
            n_type = G.nodes[neighbor_name].get("entity_type", "") if neighbor_name in G.nodes else ""
            n_color = TYPE_COLORS.get(n_type, BRAND["text_grey"])
            children.append(
                html.Div(
                    style={
                        "padding": "8px 10px",
                        "marginBottom": "4px",
                        "backgroundColor": BRAND["navy"],
                        "borderRadius": "4px",
                        "borderLeft": f"3px solid {n_color}",
                    },
                    children=[
                        html.Span(neighbor_name, style={"fontWeight": "600", "fontSize": "13px"}),
                        html.Div(
                            edge_desc,
                            style={"fontSize": "11px", "color": BRAND["text_grey"], "marginTop": "3px"},
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
                            "backgroundColor": BRAND["navy"],
                            "border": f"1px solid #2A2D4A",
                            "padding": "3px 10px",
                            "borderRadius": "12px",
                            "fontSize": "11px",
                            "marginRight": "4px",
                            "marginBottom": "4px",
                            "display": "inline-block",
                            "color": BRAND["peach"],
                        },
                    )
                )

    return [
        html.H3("Relationship", style={"margin": "0 0 10px 0", "color": BRAND["white"]}),
        html.Div(
            style={
                "padding": "14px",
                "backgroundColor": BRAND["navy"],
                "borderRadius": "8px",
                "marginBottom": "14px",
                "border": f"1px solid #2A2D4A",
            },
            children=[
                html.Span(source, style={"color": BRAND["blue"], "fontWeight": "700"}),
                html.Span(" \u2192 ", style={"color": BRAND["text_grey"], "margin": "0 10px"}),
                html.Span(target, style={"color": BRAND["orange"], "fontWeight": "700"}),
            ],
        ),
        html.Div(
            f"Weight: {weight:.1f}",
            style={"color": BRAND["text_grey"], "fontSize": "12px", "marginBottom": "12px"},
        ),
        html.Div(
            keyword_badges,
            style={"marginBottom": "16px"},
        ) if keyword_badges else None,
        html.H4("Description", style={"color": BRAND["blue"], "marginBottom": "6px", "fontSize": "14px"}),
        dcc.Markdown(
            description,
            style={"lineHeight": "1.7", "fontSize": "13px"},
        ),
    ]
