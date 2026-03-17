import { useState } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onLlmQuery: (query: string) => void;
  onClear: () => void;
  llmLoading: boolean;
}

export default function SearchBar({ onSearch, onLlmQuery, onClear, llmLoading }: SearchBarProps) {
  const [value, setValue] = useState("");

  return (
    <div className="p-4" style={{ borderBottom: "1px solid #2A2D4A" }}>
      <input
        type="text"
        placeholder="Search nodes by name or description..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") onSearch(value); }}
        className="w-full px-4 py-2.5 rounded-lg text-sm outline-none mb-3"
        style={{
          background: "#181A2E",
          border: "1px solid #2A2D4A",
          color: "#E5E7EB",
        }}
      />
      <div className="flex gap-2">
        <button
          className="btn btn-blue flex-1"
          onClick={() => onSearch(value)}
        >
          Search
        </button>
        <button
          className={`btn btn-coral flex-1 ${llmLoading ? "pulse-glow" : ""}`}
          onClick={() => onLlmQuery(value)}
          disabled={llmLoading || !value.trim()}
        >
          {llmLoading ? "Querying..." : "Ask LLM"}
        </button>
        <button
          className="btn btn-ghost"
          onClick={() => { setValue(""); onClear(); }}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
