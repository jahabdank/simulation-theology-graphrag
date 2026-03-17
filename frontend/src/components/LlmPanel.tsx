import ReactMarkdown from "react-markdown";
import { ST } from "../styles/theme";

interface LlmPanelProps {
  query: string | null;
  response: string | null;
  matchedNodes: string[];
  loading: boolean;
  error: string | null;
}

export default function LlmPanel({ query, response, matchedNodes, loading, error }: LlmPanelProps) {
  if (!query && !loading) {
    return (
      <div className="text-center py-16" style={{ color: ST.textGrey }}>
        <div className="text-sm mb-1">Type a question and click Ask LLM</div>
        <div className="text-xs opacity-60">Results will appear here</div>
      </div>
    );
  }

  return (
    <div>
      <div className="section-header" style={{ color: ST.coral }}>
        <span>LLM Query Result</span>
      </div>

      {/* Query display */}
      {query && (
        <div className="rounded-lg p-3 mb-4 text-sm italic"
          style={{
            background: ST.navy,
            borderLeft: `3px solid ${ST.coral}`,
            color: ST.textGrey,
          }}>
          "{query}"
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 py-8 justify-center">
          <div className="spinner" />
          <span className="text-sm" style={{ color: ST.textGrey }}>Querying knowledge graph...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg p-3 text-sm" style={{ color: ST.error, background: `${ST.error}15` }}>
          {error}
        </div>
      )}

      {/* Results */}
      {response && (
        <>
          {matchedNodes.length > 0 && (
            <div className="mb-3">
              <span className="text-[11px] rounded-full px-3 py-1"
                style={{ color: ST.coral, background: `${ST.coral}22` }}>
                {matchedNodes.length} related nodes highlighted
              </span>
            </div>
          )}
          <div className="markdown-content text-sm" style={{ lineHeight: "1.7" }}>
            <ReactMarkdown>{response}</ReactMarkdown>
          </div>
        </>
      )}
    </div>
  );
}
