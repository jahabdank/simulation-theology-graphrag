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

cyto.load_extra_layouts()

# --- Brand Palette ---
BRAND = {
    "blue": "#6B8CFF", "coral": "#F07050", "orange": "#F28C50",
    "peach": "#F9B870", "light_peach": "#F5C4A0",
    "navy": "#181A2E", "navy_light": "#1E2040",
    "cream": "#FAF5F0", "white": "#FFFFFF",
    "text_dark": "#1A1A2E", "text_grey": "#6B7280", "text_light": "#E5E7EB",
    "success": "#10B981", "warning": "#FFD700", "error": "#FF4444",
    "inactive": "#555555",
    "font": "'Open Sans', 'Segoe UI', system-ui, -apple-system, sans-serif",
    # Derived
    "border": "#2A2D4A",
    "glow_blue": "rgba(107, 140, 255, 0.4)",
    "glow_coral": "rgba(240, 112, 80, 0.5)",
}

TYPE_COLORS = {
    "axiom": BRAND["coral"],
    "entity": BRAND["orange"],
    "concept": BRAND["blue"],
    "architectural_component": "#8B9FFF",
    "biblical_figure": BRAND["success"],
    "religious_concept": "#B07CFF",
    "st_term": BRAND["peach"],
    "scripture_mapping": "#9CA3AF",
    "UNKNOWN": BRAND["text_grey"],
}

LAYOUT_OPTIONS = [
    {"label": "Force-directed (cose)", "value": "cose"},
    {"label": "Cola (constraint-based)", "value": "cola"},
    {"label": "Dagre (hierarchical)", "value": "dagre"},
    {"label": "Circular", "value": "circle"},
    {"label": "Concentric", "value": "concentric"},
    {"label": "Grid", "value": "grid"},
]

# Custom CSS injected into the app for the resize handle and scrollbar styling
_CUSTOM_CSS = """
/* Resizable sidebar */
#sidebar-container {
    resize: horizontal;
    overflow: hidden;
    min-width: 300px;
    max-width: 70vw;
}
#sidebar-container::-webkit-resizer {
    background: linear-gradient(135deg, transparent 40%, #6B8CFF 40%, #6B8CFF 45%, transparent 45%,
                transparent 55%, #6B8CFF 55%, #6B8CFF 60%, transparent 60%,
                transparent 70%, #6B8CFF 70%, #6B8CFF 75%, transparent 75%);
    cursor: ew-resize;
}

/* Custom scrollbar */
#detail-panel::-webkit-scrollbar {
    width: 6px;
}
#detail-panel::-webkit-scrollbar-track {
    background: #181A2E;
    border-radius: 3px;
}
#detail-panel::-webkit-scrollbar-thumb {
    background: #2A2D4A;
    border-radius: 3px;
}
#detail-panel::-webkit-scrollbar-thumb:hover {
    background: #6B8CFF;
}

/* Smooth transitions */
.dash-graph {
    transition: opacity 0.3s ease;
}

/* Button hover effects via CSS */
#search-btn:hover { filter: brightness(1.15); }
#llm-query-btn:hover:not(:disabled) { filter: brightness(1.15); }
#clear-btn:hover { background-color: #2A2D4A !important; }

/* Pulse animation for querying state */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 4px rgba(107, 140, 255, 0.3); }
    50% { box-shadow: 0 0 16px rgba(107, 140, 255, 0.6); }
}
.querying-indicator {
    animation: pulse-glow 1.5s ease-in-out infinite;
}
"""


def _load_graph_data(working_dir: Path):
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


def _build_cytoscape_elements(G: nx.Graph):
    degrees = dict(G.degree())
    elements = []
    for node_id, data in G.nodes(data=True):
        deg = degrees.get(node_id, 0)
        size = 18 + math.log1p(deg) * 13
        etype = data.get("entity_type", "UNKNOWN")
        color = TYPE_COLORS.get(etype, TYPE_COLORS["UNKNOWN"])
        elements.append({"data": {
            "id": node_id, "label": node_id, "entity_type": etype,
            "description": data.get("description", ""),
            "source_id": data.get("source_id", ""),
            "degree": deg, "size": size, "color": color,
        }})
    for u, v, data in G.edges(data=True):
        weight = float(data.get("weight", 1.0))
        elements.append({"data": {
            "source": u, "target": v, "weight": weight,
            "description": data.get("description", ""),
            "keywords": data.get("keywords", ""),
            "edge_width": max(0.5, min(weight, 5.0)),
        }})
    return elements


def _get_entity_source_text(entity_name, entity_chunks, text_chunks):
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
    return [
        # Nodes — rounded with subtle glow
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": "data(size)",
                "height": "data(size)",
                "background-color": "data(color)",
                "background-opacity": 0.85,
                "color": BRAND["text_light"],
                "font-size": "9px",
                "font-family": BRAND["font"],
                "font-weight": "500",
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": "6px",
                "text-outline-color": BRAND["navy"],
                "text-outline-width": "2px",
                "text-max-width": "90px",
                "text-wrap": "ellipsis",
                "border-width": "2px",
                "border-color": "data(color)",
                "border-opacity": 0.3,
                "overlay-padding": "4px",
                "shadow-blur": "8",
                "shadow-color": "data(color)",
                "shadow-opacity": 0.15,
                "shadow-offset-x": "0",
                "shadow-offset-y": "0",
                "transition-property": "border-width, border-color, background-opacity, shadow-opacity",
                "transition-duration": "0.2s",
            },
        },
        # Edges — gradient feel with subtle curves
        {
            "selector": "edge",
            "style": {
                "width": "data(edge_width)",
                "line-color": "#2A2D4A",
                "target-arrow-color": "#3A3D5A",
                "target-arrow-shape": "triangle",
                "arrow-scale": 0.7,
                "curve-style": "bezier",
                "opacity": 0.3,
                "line-style": "solid",
                "transition-property": "opacity, line-color, width",
                "transition-duration": "0.2s",
            },
        },
        # Hover node
        {
            "selector": "node:active",
            "style": {
                "overlay-color": BRAND["blue"],
                "overlay-opacity": 0.15,
            },
        },
        # Selected node — bright glow
        {
            "selector": "node:selected",
            "style": {
                "border-width": "3px",
                "border-color": BRAND["white"],
                "border-opacity": 1.0,
                "background-opacity": 1.0,
                "font-size": "12px",
                "font-weight": "bold",
                "shadow-blur": "20",
                "shadow-color": BRAND["coral"],
                "shadow-opacity": 0.6,
                "z-index": 9999,
            },
        },
        # Selected edge
        {
            "selector": "edge:selected",
            "style": {
                "line-color": BRAND["coral"],
                "target-arrow-color": BRAND["coral"],
                "opacity": 1.0,
                "width": 3,
            },
        },
        # Highlighted nodes (search)
        {
            "selector": ".highlighted",
            "style": {
                "border-width": "3px",
                "border-color": BRAND["warning"],
                "border-opacity": 1.0,
                "shadow-blur": "16",
                "shadow-color": BRAND["warning"],
                "shadow-opacity": 0.5,
                "font-size": "12px",
                "z-index": 9998,
            },
        },
        {"selector": ".dimmed", "style": {"opacity": 0.1}},
        {"selector": ".hidden", "style": {"display": "none"}},
    ]


_BTN_SEARCH = {
    "flex": "1", "padding": "9px 12px",
    "backgroundColor": BRAND["blue"], "color": BRAND["white"],
    "border": "none", "borderRadius": "6px", "cursor": "pointer",
    "fontFamily": BRAND["font"], "fontWeight": "600", "fontSize": "13px",
    "transition": "filter 0.15s",
}
_BTN_LLM = {
    "flex": "1", "padding": "9px 12px",
    "backgroundColor": BRAND["coral"], "color": BRAND["white"],
    "border": "none", "borderRadius": "6px", "cursor": "pointer",
    "fontFamily": BRAND["font"], "fontWeight": "600", "fontSize": "13px",
    "transition": "filter 0.15s",
}
_BTN_LLM_LOADING = {
    "flex": "1", "padding": "9px 12px",
    "backgroundColor": BRAND["inactive"], "color": BRAND["text_light"],
    "border": "none", "borderRadius": "6px", "cursor": "wait",
    "fontFamily": BRAND["font"], "fontWeight": "600", "fontSize": "13px",
}
_BTN_CLEAR = {
    "padding": "9px 14px",
    "backgroundColor": "transparent", "color": BRAND["text_grey"],
    "border": f"1px solid {BRAND['border']}", "borderRadius": "6px",
    "cursor": "pointer", "fontFamily": BRAND["font"], "fontSize": "13px",
    "transition": "background-color 0.15s",
}


def create_app(config=None):
    if config is None:
        config = load_config()

    working_dir = Path(config.lightrag.working_dir)
    G, text_chunks, entity_chunks = _load_graph_data(working_dir)
    elements = _build_cytoscape_elements(G)

    entity_types = sorted(set(
        data.get("entity_type", "UNKNOWN") for _, data in G.nodes(data=True)
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

    # Inject custom CSS
    app.index_string = '''<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>ST Knowledge Graph</title>
{%favicon%}
{%css%}
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>''' + _CUSTOM_CSS + '''</style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>'''

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
            # Header
            html.Div(
                style={
                    "padding": "12px 24px",
                    "background": f"linear-gradient(135deg, {BRAND['navy']} 0%, {BRAND['navy_light']} 100%)",
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "20px",
                    "borderBottom": f"1px solid {BRAND['border']}",
                    "flexShrink": "0",
                    "boxShadow": f"0 2px 12px rgba(0,0,0,0.3)",
                },
                children=[
                    # Logo / Title area
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px"},
                        children=[
                            # Decorative orb
                            html.Div(style={
                                "width": "32px", "height": "32px", "borderRadius": "50%",
                                "background": f"radial-gradient(circle at 35% 35%, {BRAND['blue']}, {BRAND['coral']})",
                                "boxShadow": f"0 0 12px {BRAND['glow_blue']}",
                                "flexShrink": "0",
                            }),
                            html.H3("Simulation Theology", style={
                                "margin": "0", "color": BRAND["white"],
                                "fontWeight": "700", "fontSize": "18px",
                                "letterSpacing": "0.3px",
                            }),
                            html.Span("Knowledge Graph", style={
                                "color": BRAND["blue"], "fontSize": "14px",
                                "fontWeight": "500", "opacity": "0.8",
                            }),
                        ],
                    ),
                    html.Div(style={"flex": "1"}),  # spacer
                    dcc.Dropdown(
                        id="layout-select", options=LAYOUT_OPTIONS, value="cose",
                        style={"width": "200px", "color": BRAND["text_dark"]},
                        clearable=False,
                    ),
                    dcc.Dropdown(
                        id="type-filter", options=type_filter_options, value="all",
                        style={"width": "240px", "color": BRAND["text_dark"]},
                        clearable=False,
                    ),
                    # Stats badge
                    html.Div(
                        style={
                            "backgroundColor": BRAND["navy"],
                            "border": f"1px solid {BRAND['border']}",
                            "borderRadius": "20px",
                            "padding": "5px 16px",
                            "fontSize": "12px",
                            "color": BRAND["text_grey"],
                            "whiteSpace": "nowrap",
                        },
                        children=[
                            html.Span(f"{total_nodes}", style={"color": BRAND["blue"], "fontWeight": "600"}),
                            html.Span(" nodes  ", style={"color": BRAND["text_grey"]}),
                            html.Span(f"{total_edges}", style={"color": BRAND["orange"], "fontWeight": "600"}),
                            html.Span(" edges", style={"color": BRAND["text_grey"]}),
                        ],
                    ),
                ],
            ),
            # Main content
            html.Div(
                style={"display": "flex", "flex": "1", "overflow": "hidden"},
                children=[
                    # Left sidebar (resizable)
                    html.Div(
                        id="sidebar-container",
                        style={
                            "width": "440px",
                            "minWidth": "300px",
                            "backgroundColor": BRAND["navy_light"],
                            "borderRight": f"1px solid {BRAND['border']}",
                            "display": "flex",
                            "flexDirection": "column",
                            "overflow": "hidden",
                            "boxShadow": "4px 0 20px rgba(0,0,0,0.2)",
                            "position": "relative",
                            "zIndex": "10",
                        },
                        children=[
                            # Search
                            html.Div(
                                style={
                                    "padding": "16px",
                                    "borderBottom": f"1px solid {BRAND['border']}",
                                    "flexShrink": "0",
                                    "background": f"linear-gradient(180deg, {BRAND['navy_light']} 0%, rgba(30,32,64,0.5) 100%)",
                                },
                                children=[
                                    dcc.Input(
                                        id="search-input", type="text",
                                        placeholder="Search nodes by name or description...",
                                        debounce=True,
                                        style={
                                            "width": "100%", "padding": "11px 16px",
                                            "backgroundColor": BRAND["navy"],
                                            "border": f"1px solid {BRAND['border']}",
                                            "borderRadius": "8px",
                                            "color": BRAND["text_light"],
                                            "fontSize": "14px", "fontFamily": BRAND["font"],
                                            "marginBottom": "12px", "boxSizing": "border-box",
                                            "outline": "none",
                                        },
                                    ),
                                    html.Div(
                                        style={"display": "flex", "gap": "8px"},
                                        children=[
                                            html.Button("Search", id="search-btn", style=_BTN_SEARCH),
                                            html.Button("Ask LLM", id="llm-query-btn", style=_BTN_LLM),
                                            html.Button("Clear", id="clear-btn", style=_BTN_CLEAR),
                                        ],
                                    ),
                                ],
                            ),
                            # Detail panel
                            html.Div(
                                id="detail-panel",
                                style={
                                    "flex": "1", "overflowY": "auto", "padding": "20px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "color": BRAND["text_grey"],
                                            "textAlign": "center",
                                            "marginTop": "80px",
                                        },
                                        children=[
                                            html.Div(style={
                                                "width": "48px", "height": "48px", "borderRadius": "50%",
                                                "background": f"radial-gradient(circle, {BRAND['blue']}33, transparent)",
                                                "border": f"2px solid {BRAND['border']}",
                                                "margin": "0 auto 16px auto",
                                                "display": "flex", "alignItems": "center", "justifyContent": "center",
                                            }, children=html.Span("\u2731", style={"fontSize": "20px", "color": BRAND["blue"]})),
                                            html.Div("Click a node or edge", style={"fontSize": "14px", "marginBottom": "4px"}),
                                            html.Div("to explore the knowledge graph", style={"fontSize": "12px", "opacity": "0.6"}),
                                        ],
                                    )
                                ],
                            ),
                            # Resize hint
                            html.Div(
                                "Drag edge to resize",
                                style={
                                    "textAlign": "center", "fontSize": "10px",
                                    "color": BRAND["text_grey"], "padding": "4px",
                                    "opacity": "0.5", "borderTop": f"1px solid {BRAND['border']}",
                                },
                            ),
                        ],
                    ),
                    # Graph area
                    html.Div(
                        style={"flex": "1", "position": "relative", "backgroundColor": BRAND["navy"]},
                        children=[
                            cyto.Cytoscape(
                                id="graph", elements=elements,
                                layout={"name": "cose", "animate": False, "randomize": True,
                                        "nodeRepulsion": 8000, "idealEdgeLength": 80},
                                style={"width": "100%", "height": "100%",
                                       "background": f"radial-gradient(ellipse at center, {BRAND['navy_light']} 0%, {BRAND['navy']} 70%)"},
                                stylesheet=_build_stylesheet(),
                                minZoom=0.1, maxZoom=5.0,
                            ),
                            # Legend
                            html.Div(
                                style={
                                    "position": "absolute", "bottom": "16px", "right": "16px",
                                    "backgroundColor": f"rgba(24, 26, 46, 0.95)",
                                    "padding": "12px 16px", "borderRadius": "10px",
                                    "border": f"1px solid {BRAND['border']}",
                                    "fontSize": "11px", "fontFamily": BRAND["font"],
                                    "backdropFilter": "blur(8px)",
                                    "boxShadow": "0 4px 16px rgba(0,0,0,0.3)",
                                },
                                children=[
                                    html.Div("Entity Types", style={
                                        "color": BRAND["text_grey"], "fontSize": "10px",
                                        "textTransform": "uppercase", "letterSpacing": "1px",
                                        "marginBottom": "8px", "fontWeight": "600",
                                    }),
                                ] + [
                                    html.Div(
                                        style={
                                            "display": "flex", "alignItems": "center",
                                            "gap": "8px", "marginBottom": "5px",
                                        },
                                        children=[
                                            html.Span(style={
                                                "width": "10px", "height": "10px",
                                                "borderRadius": "50%",
                                                "backgroundColor": color,
                                                "display": "inline-block",
                                                "boxShadow": f"0 0 6px {color}55",
                                            }),
                                            html.Span(etype, style={"color": BRAND["text_light"]}),
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
        stylesheet.append({"selector": "node", "style": {"opacity": 0.08, "font-size": "0px"}})
        for nid in matching_ids:
            stylesheet.append({
                "selector": f'node[id = "{nid}"]',
                "style": {
                    "opacity": 1.0, "border-width": "3px",
                    "border-color": BRAND["warning"], "border-opacity": 1.0,
                    "shadow-blur": "20", "shadow-color": BRAND["warning"],
                    "shadow-opacity": 0.5,
                    "font-size": "12px", "z-index": 9998,
                },
            })
        stylesheet.append({"selector": "edge", "style": {"opacity": 0.03}})
        return stylesheet

    @app.callback(
        Output("detail-panel", "children", allow_duplicate=True),
        Input("llm-query-btn", "n_clicks"),
        State("search-input", "value"),
        prevent_initial_call=True,
        running=[
            (Output("llm-query-btn", "disabled"), True, False),
            (Output("llm-query-btn", "children"), "Querying...", "Ask LLM"),
            (Output("llm-query-btn", "style"), _BTN_LLM_LOADING, _BTN_LLM),
        ],
        background=True,
        manager=background_callback_manager,
    )
    def handle_llm_query(n_clicks, query_text):
        if not query_text or not query_text.strip():
            return html.Div("Enter a question in the search box first.",
                            style={"color": BRAND["error"], "padding": "12px"})
        header = _make_section_header("LLM Query Result", BRAND["coral"], icon="\u2728")
        query_display = html.Div(f'"{query_text}"', style={
            "color": BRAND["text_grey"], "fontSize": "13px",
            "marginBottom": "16px", "fontStyle": "italic",
            "padding": "10px 14px", "backgroundColor": BRAND["navy"],
            "borderRadius": "8px", "borderLeft": f"3px solid {BRAND['coral']}",
        })
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
            return html.Div([header, query_display,
                             dcc.Markdown(result, style={"lineHeight": "1.7", "fontSize": "14px"})])
        except Exception as e:
            logger.error("LLM query failed: %s", e, exc_info=True)
            return html.Div([header, query_display,
                             html.Div(f"Query failed: {e}", style={"color": BRAND["error"]})])

    @app.callback(Output("graph", "layout"), Input("layout-select", "value"))
    def update_layout(layout_name):
        return {"name": layout_name, "animate": True}

    @app.callback(Output("graph", "elements"), Input("type-filter", "value"))
    def filter_by_type(selected_type):
        if selected_type == "all":
            return elements
        filtered_node_ids = set()
        filtered = []
        for el in elements:
            d = el["data"]
            if "source" not in d and d.get("entity_type") == selected_type:
                filtered.append(el)
                filtered_node_ids.add(d["id"])
        for el in elements:
            d = el["data"]
            if "source" in d and d["source"] in filtered_node_ids and d["target"] in filtered_node_ids:
                filtered.append(el)
        return filtered

    return app


# --- Render helpers ---

def _make_section_header(title, color, icon=None):
    children = []
    if icon:
        children.append(html.Span(icon, style={"marginRight": "8px"}))
    children.append(title)
    return html.H4(children, style={
        "color": color, "marginBottom": "12px", "fontSize": "15px",
        "fontWeight": "600", "display": "flex", "alignItems": "center",
        "borderBottom": f"1px solid {BRAND['border']}", "paddingBottom": "8px",
    })


def _render_node_detail(node_data, G, entity_chunks, text_chunks):
    node_id = node_data["id"]
    etype = node_data.get("entity_type", "UNKNOWN")
    description = node_data.get("description", "No description available.")
    degree = node_data.get("degree", 0)
    color = TYPE_COLORS.get(etype, TYPE_COLORS["UNKNOWN"])

    neighbors = []
    if node_id in G:
        for neighbor in G.neighbors(node_id):
            ed = G.get_edge_data(node_id, neighbor, default={})
            neighbors.append((neighbor, ed.get("description", "")[:120], "out"))
        if hasattr(G, "predecessors"):
            for pred in G.predecessors(node_id):
                if pred != node_id and pred not in [n for n, _, _ in neighbors]:
                    ed = G.get_edge_data(pred, node_id, default={})
                    neighbors.append((pred, ed.get("description", "")[:120], "in"))
    neighbors.sort(key=lambda x: x[0])
    source_text = _get_entity_source_text(node_id, entity_chunks, text_chunks)

    children = [
        # Header card
        html.Div(style={
            "padding": "16px", "borderRadius": "10px", "marginBottom": "16px",
            "background": f"linear-gradient(135deg, {BRAND['navy']} 0%, {color}15 100%)",
            "border": f"1px solid {color}33",
        }, children=[
            html.H3(node_id, style={"margin": "0 0 8px 0", "color": BRAND["white"], "fontSize": "18px"}),
            html.Div(style={"display": "flex", "gap": "8px", "flexWrap": "wrap"}, children=[
                html.Span(etype, style={
                    "backgroundColor": color, "color": BRAND["white"],
                    "padding": "4px 14px", "borderRadius": "14px",
                    "fontSize": "11px", "fontWeight": "600", "textTransform": "uppercase",
                    "letterSpacing": "0.5px",
                }),
                html.Span(f"{degree} connections", style={
                    "color": BRAND["text_grey"], "fontSize": "12px", "lineHeight": "26px",
                    "backgroundColor": f"{BRAND['navy']}aa", "padding": "2px 10px",
                    "borderRadius": "10px",
                }),
            ]),
        ]),
        # Description
        _make_section_header("Description", BRAND["blue"], icon="\U0001f4d6"),
        dcc.Markdown(description, style={
            "lineHeight": "1.75", "fontSize": "13px", "marginBottom": "16px",
            "padding": "0 4px",
        }),
    ]

    if source_text:
        children.extend([
            _make_section_header("Source Text", BRAND["success"], icon="\U0001f4c4"),
            html.Div(style={
                "padding": "14px", "borderRadius": "8px",
                "backgroundColor": f"{BRAND['navy']}",
                "border": f"1px solid {BRAND['border']}",
                "maxHeight": "300px", "overflowY": "auto",
            }, children=[
                dcc.Markdown(source_text, style={
                    "lineHeight": "1.6", "fontSize": "12px", "color": BRAND["light_peach"],
                }),
            ]),
        ])

    if neighbors:
        children.append(_make_section_header(
            f"Connections ({len(neighbors)})", BRAND["orange"], icon="\U0001f517"
        ))
        for neighbor_name, edge_desc, direction in neighbors:
            n_type = G.nodes[neighbor_name].get("entity_type", "") if neighbor_name in G.nodes else ""
            n_color = TYPE_COLORS.get(n_type, BRAND["text_grey"])
            arrow = "\u2192" if direction == "out" else "\u2190"
            children.append(html.Div(style={
                "padding": "10px 12px", "marginBottom": "6px",
                "backgroundColor": BRAND["navy"], "borderRadius": "6px",
                "borderLeft": f"3px solid {n_color}",
                "transition": "background-color 0.15s",
            }, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "6px"}, children=[
                    html.Span(arrow, style={"color": n_color, "fontSize": "12px"}),
                    html.Span(neighbor_name, style={"fontWeight": "600", "fontSize": "13px"}),
                    html.Span(n_type, style={
                        "fontSize": "9px", "color": n_color, "opacity": "0.7",
                        "marginLeft": "auto",
                    }) if n_type else None,
                ]),
                html.Div(edge_desc, style={
                    "fontSize": "11px", "color": BRAND["text_grey"],
                    "marginTop": "4px", "lineHeight": "1.4",
                }) if edge_desc else None,
            ]))

    return children


def _render_edge_detail(edge_data):
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
                keyword_badges.append(html.Span(kw, style={
                    "backgroundColor": f"{BRAND['blue']}22",
                    "border": f"1px solid {BRAND['blue']}44",
                    "padding": "3px 12px", "borderRadius": "14px",
                    "fontSize": "11px", "marginRight": "6px", "marginBottom": "6px",
                    "display": "inline-block", "color": BRAND["peach"],
                }))

    # Weight bar
    bar_width = min(weight / 6.0 * 100, 100)

    return [
        # Relationship header card
        html.Div(style={
            "padding": "16px", "borderRadius": "10px", "marginBottom": "16px",
            "background": f"linear-gradient(135deg, {BRAND['navy']} 0%, {BRAND['blue']}15 100%)",
            "border": f"1px solid {BRAND['border']}",
        }, children=[
            html.Div("Relationship", style={
                "fontSize": "10px", "textTransform": "uppercase", "letterSpacing": "1px",
                "color": BRAND["text_grey"], "marginBottom": "10px",
            }),
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap"}, children=[
                html.Span(source, style={
                    "color": BRAND["blue"], "fontWeight": "700", "fontSize": "16px",
                }),
                html.Span("\u2192", style={
                    "color": BRAND["text_grey"], "fontSize": "18px",
                }),
                html.Span(target, style={
                    "color": BRAND["orange"], "fontWeight": "700", "fontSize": "16px",
                }),
            ]),
        ]),
        # Weight indicator
        html.Div(style={"marginBottom": "16px"}, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
                html.Span("Weight", style={"fontSize": "11px", "color": BRAND["text_grey"]}),
                html.Span(f"{weight:.1f}", style={"fontSize": "11px", "color": BRAND["text_light"]}),
            ]),
            html.Div(style={
                "height": "4px", "backgroundColor": BRAND["border"], "borderRadius": "2px",
            }, children=[
                html.Div(style={
                    "height": "100%", "borderRadius": "2px",
                    "width": f"{bar_width}%",
                    "background": f"linear-gradient(90deg, {BRAND['blue']}, {BRAND['coral']})",
                }),
            ]),
        ]),
        # Keywords
        html.Div(keyword_badges, style={"marginBottom": "16px"}) if keyword_badges else None,
        # Description
        _make_section_header("Description", BRAND["blue"], icon="\U0001f4ac"),
        dcc.Markdown(description, style={"lineHeight": "1.75", "fontSize": "13px"}),
    ]
