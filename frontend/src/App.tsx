import { useState, useCallback } from "react";
import Header from "./components/Header";
import DetailPanel from "./components/DetailPanel";
import GraphView from "./components/GraphView";
import NodeDetail from "./components/NodeDetail";
import EdgeDetail from "./components/EdgeDetail";
import SearchBar from "./components/SearchBar";
import LlmPanel from "./components/LlmPanel";
import Legend from "./components/Legend";
import { useGraph } from "./hooks/useGraph";
import { useSearch } from "./hooks/useSearch";
import { useLlmQuery } from "./hooks/useLlmQuery";
import { ST } from "./styles/theme";
import type { HighlightState } from "./types";

export default function App() {
  const { graph, stats, loading, error } = useGraph();
  const search = useSearch();
  const llm = useLlmQuery();

  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{
    id: string; source: string; target: string;
  } | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"detail" | "llm">("detail");

  // Compute highlight state
  let highlightState: HighlightState = { type: "none" };
  if (llm.matchedNodes.length > 0) {
    highlightState = { type: "llm", primaryNodes: new Set(llm.matchedNodes) };
  } else if (search.results.length > 0) {
    highlightState = { type: "search", primaryNodes: new Set(search.results) };
  }

  const handleClickNode = useCallback((nodeId: string) => {
    setSelectedNode(nodeId);
    setSelectedEdge(null);
    setActiveTab("detail");
  }, []);

  const handleClickEdge = useCallback((edgeId: string, source: string, target: string) => {
    setSelectedEdge({ id: edgeId, source, target });
    setSelectedNode(null);
    setActiveTab("detail");
  }, []);

  const handleSearch = useCallback((query: string) => {
    llm.clear();
    search.execute(query);
  }, [search, llm]);

  const handleLlmQuery = useCallback((query: string) => {
    if (!query.trim()) return;
    search.clear();
    llm.execute(query);
    setActiveTab("llm");
  }, [llm, search]);

  const handleClear = useCallback(() => {
    search.clear();
    llm.clear();
    setSelectedNode(null);
    setSelectedEdge(null);
  }, [search, llm]);

  // Loading/error screens
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4"
        style={{ background: ST.navy }}>
        <div className="spinner" style={{ width: 40, height: 40, borderWidth: 4 }} />
        <div className="text-sm" style={{ color: ST.textGrey }}>Loading knowledge graph...</div>
      </div>
    );
  }

  if (error || !graph) {
    return (
      <div className="flex flex-col items-center justify-center h-screen gap-4"
        style={{ background: ST.navy }}>
        <div className="text-lg" style={{ color: ST.error }}>Failed to load graph</div>
        <div className="text-sm" style={{ color: ST.textGrey }}>{error}</div>
      </div>
    );
  }

  // Get edge data for detail panel
  const edgeData = selectedEdge && graph.hasEdge(selectedEdge.id)
    ? {
        weight: graph.getEdgeAttribute(selectedEdge.id, "weight") || 1,
        description: graph.getEdgeAttribute(selectedEdge.id, "description") || "",
        keywords: graph.getEdgeAttribute(selectedEdge.id, "keywords") || "",
      }
    : null;

  // Detail content
  const detailContent = selectedNode ? (
    <NodeDetail nodeId={selectedNode} onNodeClick={handleClickNode} />
  ) : selectedEdge ? (
    <EdgeDetail source={selectedEdge.source} target={selectedEdge.target} edgeData={edgeData} />
  ) : (
    <div className="text-center py-16" style={{ color: ST.textGrey }}>
      <div className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center"
        style={{
          background: `radial-gradient(circle, ${ST.blue}33, transparent)`,
          border: `2px solid ${ST.border}`,
        }}>
        <span className="text-xl" style={{ color: ST.blue }}>{"\u2731"}</span>
      </div>
      <div className="text-sm mb-1">Click a node or edge</div>
      <div className="text-xs opacity-60">to explore the knowledge graph</div>
    </div>
  );

  return (
    <>
      <Header stats={stats} />
      <div className="flex flex-1 overflow-hidden">
        <DetailPanel
          activeTab={activeTab}
          onTabChange={setActiveTab}
          searchBar={
            <SearchBar
              onSearch={handleSearch}
              onLlmQuery={handleLlmQuery}
              onClear={handleClear}
              llmLoading={llm.loading}
            />
          }
          detailContent={detailContent}
          llmContent={
            <LlmPanel
              query={llm.query}
              response={llm.response}
              matchedNodes={llm.matchedNodes}
              loading={llm.loading}
              error={llm.error}
            />
          }
        />
        <div className="flex-1 relative">
          <GraphView
            graph={graph}
            highlightState={highlightState}
            selectedNode={selectedNode}
            hoveredNode={hoveredNode}
            onClickNode={handleClickNode}
            onClickEdge={handleClickEdge}
            onHoverNode={setHoveredNode}
            onClickStage={() => {
              setSelectedNode(null);
              setSelectedEdge(null);
            }}
          />
          <Legend />
        </div>
      </div>
    </>
  );
}
