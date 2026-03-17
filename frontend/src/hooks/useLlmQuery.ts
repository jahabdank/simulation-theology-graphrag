import { useState, useCallback } from "react";
import { postQuery } from "../api/client";

export function useLlmQuery() {
  const [response, setResponse] = useState<string | null>(null);
  const [matchedNodes, setMatchedNodes] = useState<string[]>([]);
  const [query, setQuery] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (question: string) => {
    setLoading(true);
    setError(null);
    setQuery(question);
    try {
      const data = await postQuery(question);
      setResponse(data.response);
      setMatchedNodes(data.matched_nodes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
      setResponse(null);
      setMatchedNodes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResponse(null);
    setMatchedNodes([]);
    setQuery(null);
    setError(null);
  }, []);

  return { response, matchedNodes, query, loading, error, execute, clear };
}
