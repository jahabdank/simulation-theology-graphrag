import { useState, useCallback } from "react";
import { fetchSearch } from "../api/client";

export function useSearch() {
  const [results, setResults] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const execute = useCallback(async (query: string) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchSearch(query);
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
  }, []);

  return { results, loading, execute, clear };
}
