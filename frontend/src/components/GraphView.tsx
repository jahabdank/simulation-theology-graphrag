import { useEffect, useRef, useCallback } from "react";
import {
  SigmaContainer,
  useRegisterEvents,
  useSigma,
  useCamera,
} from "@react-sigma/core";
// sigma styles handled in index.css
import FA2Layout from "graphology-layout-forceatlas2/worker";
import Graph from "graphology";
import { ST, TYPE_COLORS } from "../styles/theme";
import type { HighlightState } from "../types";

interface GraphViewProps {
  graph: Graph;
  highlightState: HighlightState;
  selectedNode: string | null;
  hoveredNode: string | null;
  onClickNode: (nodeId: string) => void;
  onClickEdge: (edgeId: string, source: string, target: string) => void;
  onHoverNode: (nodeId: string | null) => void;
  onClickStage: () => void;
}

function GraphEvents({
  graph,
  highlightState,
  selectedNode,
  hoveredNode,
  onClickNode,
  onClickEdge,
  onHoverNode,
  onClickStage,
}: GraphViewProps) {
  const sigma = useSigma();
  const camera = useCamera();
  const layoutRef = useRef<FA2Layout | null>(null);

  // Start ForceAtlas2 layout in web worker
  useEffect(() => {
    const layout = new FA2Layout(graph, {
      settings: {
        gravity: 0.05,
        scalingRatio: 10,
        barnesHutOptimize: true,
        slowDown: 5,
        adjustSizes: true,
      },
    });
    layout.start();
    layoutRef.current = layout;

    // Stop after 3 seconds
    const timer = setTimeout(() => {
      layout.stop();
    }, 3000);

    return () => {
      clearTimeout(timer);
      layout.kill();
    };
  }, [graph]);

  // Register events
  useRegisterEvents({
    clickNode: (e) => {
      onClickNode(e.node);
      const pos = sigma.getNodeDisplayData(e.node);
      if (pos) {
        camera.animate(
          { x: pos.x, y: pos.y, ratio: 0.4 },
          { duration: 600 }
        );
      }
    },
    clickEdge: (e) => {
      const source = graph.source(e.edge);
      const target = graph.target(e.edge);
      onClickEdge(e.edge, source, target);
    },
    enterNode: (e) => onHoverNode(e.node),
    leaveNode: () => onHoverNode(null),
    clickStage: () => onClickStage(),
  });

  // Enable edge events
  useEffect(() => {
    sigma.setSetting("enableEdgeClickEvents", true);
    sigma.setSetting("enableEdgeHoverEvents", true);
  }, [sigma]);

  // Node + edge reducers for highlighting
  useEffect(() => {
    const neighborCache = new Map<string, Set<string>>();
    const getNeighbors = (nodeId: string): Set<string> => {
      if (neighborCache.has(nodeId)) return neighborCache.get(nodeId)!;
      const neighbors = new Set<string>();
      graph.forEachNeighbor(nodeId, (n) => neighbors.add(n));
      neighborCache.set(nodeId, neighbors);
      return neighbors;
    };

    sigma.setSetting("nodeReducer", (node, data) => {
      const res = { ...data };

      // Highlight state (search or LLM)
      if (highlightState.type !== "none") {
        const isPrimary = highlightState.primaryNodes.has(node);
        let isRelated = false;
        if (!isPrimary) {
          for (const pn of highlightState.primaryNodes) {
            if (getNeighbors(pn).has(node)) { isRelated = true; break; }
          }
        }

        if (isPrimary) {
          res.color = highlightState.type === "llm" ? ST.coral : ST.orange;
          res.size = (data.size || 10) * 1.3;
          res.zIndex = 2;
          res.highlighted = true;
        } else if (isRelated) {
          res.color = highlightState.type === "llm" ? ST.blue : ST.peach;
          res.size = (data.size || 10) * 1.1;
          res.zIndex = 1;
        } else {
          res.color = "#222233";
          res.size = (data.size || 10) * 0.6;
          res.label = "";
          res.zIndex = 0;
        }
      }

      // Selected node
      if (node === selectedNode) {
        res.highlighted = true;
        res.zIndex = 3;
      }

      // Hovered node
      if (node === hoveredNode) {
        res.size = (res.size || 10) * 1.2;
        res.highlighted = true;
        res.zIndex = 3;
      }

      return res;
    });

    sigma.setSetting("edgeReducer", (edge, data) => {
      const res = { ...data };
      const source = graph.source(edge);
      const target = graph.target(edge);

      if (highlightState.type !== "none") {
        const allVisible = new Set(highlightState.primaryNodes);
        for (const pn of highlightState.primaryNodes) {
          getNeighbors(pn).forEach((n) => allVisible.add(n));
        }
        if (allVisible.has(source) && allVisible.has(target)) {
          const bothPrimary =
            highlightState.primaryNodes.has(source) &&
            highlightState.primaryNodes.has(target);
          res.color = bothPrimary
            ? (highlightState.type === "llm" ? ST.coral : ST.orange)
            : (highlightState.type === "llm" ? ST.blue : ST.peach);
          res.size = 1.5;
          res.hidden = false;
        } else {
          res.color = "#111122";
          res.size = 0.3;
        }
      }

      // Hovered node — show its edges
      if (hoveredNode && (source === hoveredNode || target === hoveredNode)) {
        res.color = ST.blue;
        res.size = 2;
        res.zIndex = 1;
      }

      return res;
    });

    sigma.refresh();
  }, [sigma, graph, highlightState, selectedNode, hoveredNode]);

  return null;
}

export default function GraphView(props: GraphViewProps) {
  return (
    <div style={{ flex: 1, position: "relative" }}>
      <SigmaContainer
        graph={props.graph}
        className="sigma-container"
        settings={{
          renderLabels: true,
          labelFont: "Open Sans",
          labelSize: 12,
          labelWeight: "500",
          labelColor: { color: ST.textLight },
          labelRenderedSizeThreshold: 8,
          defaultEdgeType: "arrow",
          edgeLabelFont: "Open Sans",
          defaultNodeColor: ST.blue,
          defaultEdgeColor: "#2A2D4A",
          stagePadding: 40,
          zoomDuration: 300,
        }}
      >
        <GraphEvents {...props} />
      </SigmaContainer>
    </div>
  );
}
