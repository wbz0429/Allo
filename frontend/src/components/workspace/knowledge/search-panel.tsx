"use client";

import { SearchIcon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/core/i18n/hooks";
import {
  useKeywordSearch,
  useSearchKnowledgeBase,
} from "@/core/knowledge/hooks";
import type { KeywordSearchResult, SearchResult } from "@/core/knowledge/types";

export function SearchPanel({ kbId }: { kbId: string }) {
  const { t } = useI18n();
  const semanticMutation = useSearchKnowledgeBase(kbId);
  const keywordMutation = useKeywordSearch(kbId);
  const [query, setQuery] = useState("");
  const [semanticResults, setSemanticResults] = useState<SearchResult[]>([]);
  const [keywordResults, setKeywordResults] = useState<KeywordSearchResult[]>(
    [],
  );
  const [activeTab, setActiveTab] = useState("keyword");

  const handleKeywordSearch = useCallback(async () => {
    if (!query.trim()) return;
    try {
      const data = await keywordMutation.mutateAsync({ query: query.trim() });
      setKeywordResults(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : t.knowledge.keywordSearchFailed,
      );
    }
  }, [query, keywordMutation, t.knowledge.keywordSearchFailed]);

  const handleSemanticSearch = useCallback(async () => {
    if (!query.trim()) return;
    try {
      const data = await semanticMutation.mutateAsync({ query: query.trim() });
      setSemanticResults(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : t.knowledge.semanticSearchFailed,
      );
    }
  }, [query, semanticMutation, t.knowledge.semanticSearchFailed]);

  const handleSearch = useCallback(() => {
    if (activeTab === "keyword") {
      void handleKeywordSearch();
    } else {
      void handleSemanticSearch();
    }
  }, [activeTab, handleKeywordSearch, handleSemanticSearch]);

  const isPending =
    activeTab === "keyword"
      ? keywordMutation.isPending
      : semanticMutation.isPending;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2">
        <Input
          placeholder={t.knowledge.searchPlaceholder}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
        />
        <Button onClick={handleSearch} disabled={!query.trim() || isPending}>
          <SearchIcon className="mr-1 size-4" />
          {isPending ? t.knowledge.searching : t.knowledge.searchButton}
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList variant="line">
          <TabsTrigger value="keyword">{t.knowledge.keywordSearch}</TabsTrigger>
          <TabsTrigger value="semantic">{t.knowledge.semanticSearch}</TabsTrigger>
        </TabsList>

        <TabsContent value="keyword" className="mt-4">
          {keywordResults.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-muted-foreground text-xs">
                {t.knowledge.resultCount(keywordResults.length)}
              </p>
              {keywordResults.map((result, i) => (
                <div key={`${result.doc_id}-${i}`} className="rounded-lg border p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <Badge variant="outline">{result.filename}</Badge>
                    <span className="text-muted-foreground text-xs">
                      {result.score.toFixed(0)} {t.knowledge.matches}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm">
                    {result.snippet}
                  </p>
                </div>
              ))}
            </div>
          )}
          {!keywordMutation.isPending &&
            keywordResults.length === 0 &&
            keywordMutation.isSuccess && (
              <div className="text-muted-foreground py-8 text-center text-sm">
                {t.knowledge.noResults}
              </div>
            )}
        </TabsContent>

        <TabsContent value="semantic" className="mt-4">
          {semanticResults.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-muted-foreground text-xs">
                {t.knowledge.resultCount(semanticResults.length)}
              </p>
              {semanticResults.map((result, i) => (
                <div
                  key={result.chunk.id ?? i}
                  className="rounded-lg border p-4"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Badge variant="outline">
                      {(result.score * 100).toFixed(1)}% {t.knowledge.relevance}
                    </Badge>
                    <span className="text-muted-foreground text-xs">
                      {t.knowledge.chunk} #{result.chunk.chunk_index + 1}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm">
                    {result.chunk.content}
                  </p>
                </div>
              ))}
            </div>
          )}
          {!semanticMutation.isPending &&
            semanticResults.length === 0 &&
            semanticMutation.isSuccess && (
              <div className="text-muted-foreground py-8 text-center text-sm">
                {t.knowledge.noResultsIndexHint}
              </div>
            )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
