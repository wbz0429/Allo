"use client";

import { SearchIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSearchKnowledgeBase } from "@/core/knowledge/hooks";
import type { SearchResult } from "@/core/knowledge/types";

export function SearchPanel({ kbId }: { kbId: string }) {
  const searchMutation = useSearchKnowledgeBase(kbId);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    try {
      const data = await searchMutation.mutateAsync({ query: query.trim() });
      setResults(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Search failed");
    }
  }, [query, searchMutation]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Input
          placeholder="Search knowledge base..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void handleSearch();
          }}
        />
        <Button
          onClick={() => void handleSearch()}
          disabled={!query.trim() || searchMutation.isPending}
        >
          <SearchIcon className="mr-1 size-4" />
          {searchMutation.isPending ? "Searching..." : "Search"}
        </Button>
      </div>

      {results.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-muted-foreground text-xs">
            {results.length} result{results.length !== 1 ? "s" : ""}
          </p>
          {results.map((result, i) => (
            <div
              key={result.chunk.id ?? i}
              className="rounded-lg border p-4"
            >
              <div className="mb-2 flex items-center gap-2">
                <Badge variant="outline">
                  {(result.score * 100).toFixed(1)}% relevance
                </Badge>
                <span className="text-muted-foreground text-xs">
                  Chunk #{result.chunk.chunk_index + 1}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-sm">
                {result.chunk.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {!searchMutation.isPending &&
        results.length === 0 &&
        searchMutation.isSuccess && (
          <div className="text-muted-foreground py-8 text-center text-sm">
            No results found
          </div>
        )}
    </div>
  );
}
